# Session Summary: Beer RAG `answer.py` v0.1

**Date:** 2026-04-28
**Branch:** main

## What We Did
- Built `sandbox/beer_rag_app/answer.py` from empty file to working v0.1 RAG pipeline
- Three functions: `fetch_content`, `make_rag_messages`, `answer_question`
- Composed: embed query → Chroma retrieval (top-K) → prompt assembly → OpenAI chat completion → return `(answer, chunks)` tuple
- Refactored shared constants out of `ingest.py` (`COLLECTION_NAME`) to enable DRY import in `answer.py`
- Used direct OpenAI SDK (deferred litellm to later in week)
- End-to-end smoke test working with real Sam Adams query against ~6964-chunk vector store

## Key Learnings

### RAG mechanics
- Same embedding model required for both ingest and query; mismatch = silent garbage retrieval (vectors live in different spaces, cosine distance returns numbers but they're meaningless). Bedrock rule, hardest bug class to spot.
- Chroma's `collection.query()` returns nested-list shape: outer list = one slot per query (batch API), inner list = one entry per K result. Single query → always `[0]` to peel outer.
- All keys (`ids`, `documents`, `metadatas`, `distances`) are parallel arrays aligned by index. `zip()`s the natural way to iterate.
- Prepending `f"Extract from {source}:\n{content}"` to each chunk in the system prompt does two things: (1) acts as a fence between concatenated chunks, (2) gives the LLM a citation anchor it can name in its answer. Without filenames in the prompt, citations are impossible.
- Cosine distance interpretation: <0.4 = paraphrase-tier match; 0.6–0.75 = relevant but varied (typical and good); >0.85 = noise. Today's results clustered 0.63–0.72 — healthy.

### Python imports (Apex → Python gap)
- Any `.py` file in the same directory is importable by name; no package, no `__init__.py`, no install needed. User had assumed otherwise.
- `.ipynb` notebooks are JSON, not Python source — cannot be imported by the standard import machinery.
- `import x` *executes* the module top-to-bottom. Top-level code runs at import time. `if __name__ == "__main__":` exists to gate code that should only run when the file is executed directly.
- `__main__` is a string literal in the comparison — `if __name__ == "__main__":`, not `if __name__ == __main__:` (latter throws NameError because Python looks for an undefined variable).

### IDE autocomplete traps
- PyCharm autocomplete will gladly inject imports that don't work: `from jedi.inference.compiled.subprocess import __main__` (jedi is PyCharm's internal autocomplete library, not user code) and `from sandbox.RAG_Beer_Intel import collection` (notebook, not importable). Both observed this session.
- Habit: review imports after typing dunders or names that exist in workspace; run module load (`python -c "import answer"`) as cheapest smoke test.

### LLM message structure
- `messages = [system] + history + [{user}]`. Position dictates "what am I responding to." Last `user` message = the prompt. Putting new question elsewhere → model responds to the wrong turn.
- System prompt > user prompt for context: instruction-precedence weighting, prompt-cache friendliness (when the system part is stable), mental-model match.

## Decisions Made
- **Day-1 scope:** strip Ed Donner's full pipeline to bare bones — drop rewriter, reranker, retry decorator, litellm. Build skeleton first, layer features later. Justified to avoid premature complexity and to keep the L3 fundamentals visible.
- **Shared types via direct import** (`from ingest import Result, DB_NAME, EMBEDDING_MODEL, COLLECTION_NAME`) rather than duplicating or extracting to `models.py`. Trade noted: couples `answer.py` to `ingest.py`. Acceptable for two-file project; revisit when a 3rd module needs the same types.
- **Module-level Chroma + OpenAI clients** rather than per-call instantiation. Avoids cold-disk overhead on every call. Will need revisit if multi-process server is added.
- **Direct OpenAI SDK** for v0.1; litellm deferred to later in week. Lets user understand the response shape before adding the abstraction layer.
- **Return tuple `(answer, chunks)`** instead of just answer. Enables citations, debug visibility, eval harness — all cheap to keep, expensive to add back later.

## Gotchas & Warnings
- `OPEN_AI_MODEL = "openai/gpt-4.1-nano"` (litellm prefix) → 400 invalid model ID with OpenAI SDK. Drop the `openai/` prefix when not using litellm.
- `__main__` must be quoted in `if __name__ == "__main__":` — easy to forget.
- Calling `fetch_content(...)` at module top-level (outside `__main__` guard) fires the embedding API on import. Will trigger every time `app.py` does `from answer import answer_question`. Always gate test calls.
- `print(s[:300])` slicing is display-truncation — does **not** mean the underlying string is short. Caused a "system prompt isn't loading fully" misdiagnosis this session.
- Bullets inside one chunk are not separate chunks. `len(results['documents'][0])` is the chunk count, not a count of bulletpoints rendered visually.
- Markdown rendering during `print()` makes chunk boundaries invisible — wrap with explicit delimiters when debugging.

## Follow-Up Items
- [ ] Remove debug `print` on line 35 of `answer.py` before committing
- [ ] Optional rename `OPEN_AI_MODEL` → `MODEL` for clarity vs `EMBEDDING_MODEL`
- [ ] `app.py` — wire `answer_question` to Gradio UI
- [ ] Eval harness: golden Q/A set, retrieval recall@K, answer faithfulness, citation accuracy
- [ ] Add `@retry(wait=wait)` on `answer_question` and `fetch_content` (handles transient 429/5xx)
- [ ] Query rewriter (Ed's pattern, line 89-107)
- [ ] Reranker (Ed's pattern, line 53-74)
- [ ] Prompt-injection consideration: vault content lands in system prompt; chunk containing "ignore previous instructions" could derail. Day-N hardening.
- [ ] Migrate to litellm once direct SDK is comfortable, to enable multi-provider experiments

## Compound Engineering Review

| Question | Finding | Action |
|----------|---------|--------|
| Implicit knowledge used? | Same-embedding-model rule, Chroma response shape, `__main__` guard semantics, citation-via-source-prefix pattern. None encoded in CLAUDE.md. | Add a short "RAG conventions" section to project CLAUDE.md or `sandbox/beer_rag_app/README.md` capturing the 4 rules. Saved separately to memory file `user_python_imports_gap.md` for the import-gap teaching context. |
| Manual workflow repeated? | Skeleton-then-fill workflow worked well: empty file → imports + constants → module-level clients → function signatures → bodies one at a time. Was guided by Socratic Q&A. | Could become a `/scaffold-py-module` skill: prompts for imports, constants, exposes a fill-in-the-blanks template with smoke-test scaffold. Low priority — only useful if the pattern recurs across modules. |
| Quality issue caught late? | IDE-autocomplete-injected bogus imports (`jedi`, `RAG_Beer_Intel`) only surfaced at runtime crash. Could be caught earlier. | Pre-commit hook idea: `python -c "import <module>"` smoke test on changed `.py` files. Or simpler: a hook that flags `from jedi.` or any import path containing `.ipynb` references. |
| Agent struggled? | Mentor-mode worked well; main friction was occasionally moving too fast (user had to ask for slowdown twice — first on "where does Ed embed the query," then on a few questions). | Update teaching-cadence memory to be more conservative on pacing: pause after each Socratic question for confirmation before stacking more. Already captured in existing `feedback_teaching_cadence.md` — reinforces don't drift from it. |
