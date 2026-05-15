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
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

_trace_logger = logging.getLogger("soto.trace")
_TRACE_PATH = os.environ.get("SOTO_TRACE_PATH")  # optional local file sink
_TRACE_PREVIEW_CHARS = 500  # tool result preview length in trace records


def _emit_trace(record: dict) -> None:
    """Emit one structured trace record.

    Always logged as a JSON line at INFO level so Container App stdout captures
    it. If SOTO_TRACE_PATH is set, also appended to that file (useful for local
    CLI debugging — `tail -f $SOTO_TRACE_PATH | jq .`).
    """
    record.setdefault("ts", datetime.now(timezone.utc).isoformat())
    line = json.dumps(record, default=str)
    _trace_logger.info(line)
    if _TRACE_PATH:
        try:
            with open(_TRACE_PATH, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass  # trace is best-effort; never fail the agent over it


def _preview(text: str | None, max_len: int = _TRACE_PREVIEW_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"...[+{len(text) - max_len} chars]"

from soto_agent.tools.wiki import WikiPage, wiki_read, wiki_search
from soto_agent.tools.glossary_lookup import glossary_lookup, GlossaryEntry
from soto_agent.tools.databricks_query import ask_genie, execute_sql, get_depletion_schema

load_dotenv()

DEFAULT_MODEL = os.getenv("SOTO_MODEL", "gpt-4.1-mini")

_PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (_PROMPTS_DIR / "system_prompt.md").read_text()

# Hard cap to prevent runaway tool-call loops.
# 20 accommodates models that don't parallelize tool calls (e.g., DeepSeek V3
# returns one tool_call per turn). gpt-4.1 / gpt-4.1-mini typically converge
# in 3-5 turns via parallel calls.
MAX_TURNS = 20


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
    {
        "type": "function",
        "function": {
            "name" : "glossary_lookup",
            "description": (
                "Read glossary of business specific terminology to uncover meaning of words that might be ambgious or "
                "have different meaning in business context. Use this to help shape exploration of the wiki or to rewrite a"
                "query"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": (
                            "The term that might have meaning specific to the Boston Beer Company"
                            "e.g. 'Account Visit"
                        ),
                    } ,
                },
                "required": ["term"],
                "additionalProperties": False,
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_depletion_schema",
            "description": (
                "Return curated schema documentation for the BBC Databricks `dev.depletion` "
                "tables (fact_depletionweeklyvariance, vw_fact_depletion, fact_market_depletion_bbc). "
                "Use this BEFORE calling execute_sql so you know which table answers your question "
                "and what columns are available. Free / fast — no warehouse query."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_genie",
            "description": (
                "Ask the BBC Sales Enablement Genie space a natural-language question. "
                "Genie has a curated semantic model over a wider set of tables than the "
                "3-table depletion schema. Prefer Genie when: (a) the question spans tables "
                "beyond depletion, (b) you can't form clean SQL, or (c) execute_sql returned "
                "empty/wrong results and you want a second opinion. For simple depletion "
                "lookups where the schema is clear, prefer execute_sql — it's faster. "
                "Returns text + generated SQL + result rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural-language question for Genie.",
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
            "name": "execute_sql",
            "description": (
                "Execute read-only SQL on the BBC Databricks Serverless SQL Warehouse. "
                "PRECONDITION: you MUST have called get_depletion_schema earlier in this conversation. "
                "If you have not called it, call it FIRST — do not guess column names. "
                "Databricks SQL is case-sensitive and will reject hallucinated columns; "
                "this wastes a turn every time. "
                "Other rules: anchor date filters to MAX(dtSalesWeekEnd), not current_date() "
                "(data has ingestion lag). Always use LIMIT (default 50). No DDL, no DML."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "SQL SELECT statement. Use fully-qualified names like "
                            "`dev.depletion.fact_depletionweeklyvariance`."
                        ),
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]

_DISPATCH = {
    "wiki_search": lambda args: wiki_search(args["question"]),
    "wiki_read": lambda args: wiki_read(args["name"]),
    "glossary_lookup" : lambda args: glossary_lookup(args["term"]),
    "get_depletion_schema": lambda args: get_depletion_schema(),
    "execute_sql": lambda args: execute_sql(args["query"]),
    "ask_genie": lambda args: ask_genie(args["question"]),
}


def _serialize_tool_result(result) -> str:
    if isinstance(result, BaseModel):
        return result.model_dump_json()

    return json.dumps(result)


def run_agent(
    question: str,
    *,
    verbose: bool = False,
    model: str | None = None,
    run_id: str | None = None,
) -> str:
    """Run the SOTO Agent loop on a single question. Returns final answer text.

    Trace records are emitted to the `soto.trace` logger as JSON lines, one per
    phase (run_start, tool_call, tool_result, tool_error, final, run_end). All
    records share a `run_id` so a downstream consumer can group them.
    """
    model_name = model or DEFAULT_MODEL
    client, deployment, extra_kwargs = _resolve_model(model_name)
    run_id = run_id or str(uuid.uuid4())
    run_start_ts = time.monotonic()

    _emit_trace({
        "run_id": run_id,
        "phase": "run_start",
        "model": model_name,
        "question_preview": _preview(question, 300),
    })

    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for turn in range(MAX_TURNS):
        turn_start_ts = time.monotonic()
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=TOOLS,
            **extra_kwargs,
        )
        msg = response.choices[0].message
        messages.append(msg)
        llm_elapsed_ms = (time.monotonic() - turn_start_ts) * 1000

        if not msg.tool_calls:
            if verbose:
                print(f"[turn {turn}] FINAL ANSWER")
            _emit_trace({
                "run_id": run_id,
                "phase": "final",
                "turn": turn,
                "llm_elapsed_ms": round(llm_elapsed_ms, 1),
                "answer_preview": _preview(msg.content or "", 500),
            })
            _emit_trace({
                "run_id": run_id,
                "phase": "run_end",
                "total_elapsed_ms": round((time.monotonic() - run_start_ts) * 1000, 1),
                "turns_used": turn + 1,
                "outcome": "ok",
            })
            return msg.content or ""

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            if verbose:
                print(f"[turn {turn}] {tc.function.name}({args})")
            _emit_trace({
                "run_id": run_id,
                "phase": "tool_call",
                "turn": turn,
                "tool_name": tc.function.name,
                "tool_args": args,
            })
            tool_start = time.monotonic()
            try:
                result = _DISPATCH[tc.function.name](args)
                content = _serialize_tool_result(result)
                tool_elapsed_ms = (time.monotonic() - tool_start) * 1000
                _emit_trace({
                    "run_id": run_id,
                    "phase": "tool_result",
                    "turn": turn,
                    "tool_name": tc.function.name,
                    "elapsed_ms": round(tool_elapsed_ms, 1),
                    "result_preview": _preview(content),
                })
            except Exception as e:
                content = json.dumps({"error": type(e).__name__, "message": str(e)})
                if verbose:
                    print(f"  -> ERROR: {content}")
                _emit_trace({
                    "run_id": run_id,
                    "phase": "tool_error",
                    "turn": turn,
                    "tool_name": tc.function.name,
                    "elapsed_ms": round((time.monotonic() - tool_start) * 1000, 1),
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:300],
                })
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                }
            )

    _emit_trace({
        "run_id": run_id,
        "phase": "run_end",
        "total_elapsed_ms": round((time.monotonic() - run_start_ts) * 1000, 1),
        "turns_used": MAX_TURNS,
        "outcome": "max_turns_exceeded",
    })
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
