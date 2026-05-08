"""SOTO Agent — outer agent loop.

Wires the wiki retrieval primitives (wiki_search, wiki_read) to gpt-4.1-mini
via OpenAI tool calling. The model decides when to search, which pages to read,
when to follow wikilinks, and when it has enough context to answer.

This is intentionally a thin loop — no streaming, no FastAPI, no Salesforce
publish path yet. Step 5 wraps run_agent() in a FastAPI route. Step 7 wires the
SF round-trip.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

from soto_agent.tools.wiki import WikiPage, wiki_read, wiki_search

load_dotenv()

_client = AzureOpenAI(
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)
_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"]

_PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (_PROMPTS_DIR / "system_prompt.md").read_text()

# Hard cap to prevent runaway tool-call loops. Each turn is one model call;
# typical answers should converge in 3-6 turns.
MAX_TURNS = 12

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


def run_agent(question: str, *, verbose: bool = False) -> str:
    """Run the SOTO Agent loop on a single question. Returns final answer text."""
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for turn in range(MAX_TURNS):
        response = _client.chat.completions.create(
            model=_DEPLOYMENT,
            messages=messages,
            tools=TOOLS,
            temperature=0.2,
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
    import sys

    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the on-premise strategy for Sun Cruiser this quarter?"
    print(f"Q: {q}\n")
    answer = run_agent(q, verbose=True)
    print(f"\nA: {answer}")
