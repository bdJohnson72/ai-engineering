"""SOTO Agent — outer agent loop.

Wires the wiki retrieval primitives (wiki_search, wiki_read) to the chosen
chat model via OpenAI tool calling. The model decides when to search, which
pages to read, when to follow wikilinks, and when it has enough context.

Models supported (env: SOTO_MODEL or --model flag):
- gpt-4.1-mini (default) — fast, cheap, BBC-tenant Foundry deployment
- deepseek-r1            — reasoning model, BBC-tenant Foundry deployment

This is intentionally a thin loop — no streaming, no FastAPI, no Salesforce
publish path yet. Step 5 wraps run_agent() in a FastAPI route. Step 7 wires
the SF round-trip.
"""

import json
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

from soto_agent.tools.wiki import WikiPage, wiki_read, wiki_search

load_dotenv()

DEFAULT_MODEL = os.getenv("SOTO_MODEL", "gpt-4.1-mini")

_PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (_PROMPTS_DIR / "system_prompt.md").read_text()

# Hard cap to prevent runaway tool-call loops.
MAX_TURNS = 12


def _build_gpt41mini() -> tuple[Any, str, dict]:
    client = AzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"]
    extra_kwargs = {"temperature": 0.2}
    return client, deployment, extra_kwargs


def _build_gpt41() -> tuple[Any, str, dict]:
    # Same Foundry resource as gpt-4.1-mini, just a larger deployment.
    client = AzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    deployment = os.environ["AZ_GPT_FOUR_ONE"]
    extra_kwargs = {"temperature": 0.2}
    return client, deployment, extra_kwargs


def _build_gpt5() -> tuple[Any, str, dict]:
    # GPT-5 family supports OpenAI tool calling. Same Foundry resource pattern
    # as gpt-4.1-mini. Set AZURE_OPENAI_DEPLOYMENT_GPT5 to your deployment name.
    client = AzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_GPT5"]
    extra_kwargs = {"temperature": 0.2}
    return client, deployment, extra_kwargs


def _build_gpt5_mini() -> tuple[Any, str, dict]:
    client = AzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_GPT5_MINI"]
    extra_kwargs = {"temperature": 0.2}
    return client, deployment, extra_kwargs


def _build_deepseek_r1() -> tuple[Any, str, dict]:
    # NOTE: Azure-hosted DeepSeek R1 does NOT support tool calling
    # ('UnsupportedToolUse' 400 from /chat/completions). Kept here for
    # potential future use as an LLM-as-judge in evals (no tools needed).
    # Do NOT use as the agent's chat model.
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    client = OpenAI(
        base_url=os.environ["AZ_DEEPSEEK_R1_URL"],
        api_key=api_key,
        default_headers={"api-key": api_key},
    )
    deployment = os.environ["AZ_DEEP_SEEK_R1"]
    extra_kwargs: dict = {}
    return client, deployment, extra_kwargs


def _build_deepseek_v3() -> tuple[Any, str, dict]:
    # DeepSeek V3.1 — non-reasoning chat model, supports OpenAI tool calling.
    # Same Foundry v1 surface as R1 (foundry-itbs-poc-2.services.ai.azure.com).
    # Reuses AZ_DEEPSEEK_R1_URL since both deployments share the resource URL;
    # set AZ_DEEPSEEK_V3 to the V3 deployment name.
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    client = OpenAI(
        base_url=os.environ["AZ_DEEPSEEK_R1_URL"],
        api_key=api_key,
        default_headers={"api-key": api_key},
    )
    deployment = os.environ["AZ_DEEPSEEK_THREE_ONE"]
    extra_kwargs = {"temperature": 0.2}
    return client, deployment, extra_kwargs


_MODEL_BUILDERS: dict[str, Callable[[], tuple[Any, str, dict]]] = {
    "gpt-4.1-mini": _build_gpt41mini,
    "gpt-4.1": _build_gpt41,
    "gpt-5": _build_gpt5,
    "gpt-5-mini": _build_gpt5_mini,
    "deepseek-v3": _build_deepseek_v3,
    "deepseek-r1": _build_deepseek_r1,  # not usable for agent; reserved for eval judge
}

_model_cache: dict[str, tuple[Any, str, dict]] = {}


def _resolve_model(model_name: str) -> tuple[Any, str, dict]:
    if model_name not in _MODEL_BUILDERS:
        raise ValueError(
            f"Unknown model {model_name!r}. Options: {sorted(_MODEL_BUILDERS)}"
        )
    if model_name not in _model_cache:
        _model_cache[model_name] = _MODEL_BUILDERS[model_name]()
    return _model_cache[model_name]


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "wiki_search",
            "description": (
                "Search the BBC wiki index for pages relevant to a question. "
                "Returns up to 8 page paths picked by an LLM from index.md. "
                "Call this first for any open-ended question about BBC concepts, "
                "strategy, products, or industry context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Free-form question. Be specific — vague queries return less-relevant pages.",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wiki_read",
            "description": (
                "Read a single wiki page by name or relative path. Returns the "
                "page body plus a list of [[wikilinks]] discovered inside. Use "
                "after wiki_search to drill into a page, or to follow a wikilink "
                "from a previously read page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Page name (e.g., 'Sun Cruiser') or relative path "
                            "(e.g., 'sources/CBD 2025-02-05 Boston Beer Sun Cruiser Investment')."
                        ),
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
]

_DISPATCH = {
    "wiki_search": lambda args: wiki_search(args["question"]),
    "wiki_read": lambda args: wiki_read(args["name"]),
}


def _serialize_tool_result(result) -> str:
    if isinstance(result, WikiPage):
        return result.model_dump_json()
    return json.dumps(result)


def run_agent(question: str, *, verbose: bool = False, model: str | None = None) -> str:
    """Run the SOTO Agent loop on a single question. Returns final answer text."""
    model_name = model or DEFAULT_MODEL
    client, deployment, extra_kwargs = _resolve_model(model_name)

    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for turn in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=TOOLS,
            **extra_kwargs,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            if verbose:
                print(f"[turn {turn}] FINAL ANSWER")
            return msg.content or ""

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            if verbose:
                print(f"[turn {turn}] {tc.function.name}({args})")
            try:
                result = _DISPATCH[tc.function.name](args)
                content = _serialize_tool_result(result)
            except Exception as e:
                content = json.dumps({"error": type(e).__name__, "message": str(e)})
                if verbose:
                    print(f"  -> ERROR: {content}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                }
            )

    return "Agent exceeded MAX_TURNS without finishing. Partial state in logs."


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SOTO Agent CLI")
    parser.add_argument("question", nargs="*", help="Question to ask")
    parser.add_argument(
        "--model",
        default=None,
        choices=sorted(_MODEL_BUILDERS),
        help=f"Model to use (default: {DEFAULT_MODEL} from SOTO_MODEL env)",
    )
    args = parser.parse_args()

    q = " ".join(args.question) if args.question else "What is BBC's on-premise strategy for Sun Cruiser?"
    model_name = args.model or DEFAULT_MODEL
    print(f"Q: {q}")
    print(f"Model: {model_name}\n")
    answer = run_agent(q, verbose=True, model=model_name)
    print(f"\nA: {answer}")
