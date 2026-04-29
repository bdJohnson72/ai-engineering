# Current Learning Plan — Beer RAG Sprint

> **Session restart pointer (last updated 2026-04-28):** If restarting, read in this order: (1) this plan, (2) `~/.claude/projects/-Users-brooksjohnson-ai-engineering/memory/MEMORY.md` and the files it points to (auto-loaded but worth confirming), (3) `sandbox/beer_rag_app/ingest.py` for current code state, (4) `sandbox/beer_rag_app/vector_db/` exists on disk with 6964 vectors persisted.
>
> **Where we are (end of Mon 2026-04-27 work session):** Full ingest pipeline complete and verified end-to-end on the entire vault: **1457 docs → 7128 chunks → 6964 unique vectors persisted to Chroma** (collection `beer_rag` at `sandbox/beer_rag_app/vector_db/`). Pipeline path: `get_vault_docs → load_document → strip_frontmatter → split_on_headings → char_window → create_chunks → create_embeddings (batched, deduped) → Chroma upsert (batched)`. Bug history along the way (all resolved): empty page_content from heading-only sections; SHA-256 ID collisions from cross-file boilerplate; OpenAI 300K-token-per-request cap; Chroma ~5461-per-call upsert cap.
>
> **Immediate handoff state:** Day 1 carryover still has **two pieces left** before Day 2 (eval baseline) can start: `answer.py` and `app.py`. The assistant is paused on `answer.py`'s system prompt design — three open decisions waiting on the user (refuse-vs-hedge behavior, citation behavior, context formatting) plus a `top_k` value (plan suggests 8). Once those are decided, user writes `answer.py`; assistant reviews. Then `app.py` (small Gradio wrapper) finishes Day 1.
>
> **Operational TODOs flagged but deferred:**
> - Re-running `ingest.py` currently re-embeds the whole corpus (~$0.02 each run). Add `--reingest` flag gating later if iteration cost becomes annoying.
> - Debug print at `ingest.py:80` (`print(all_files[:5])` inside `get_vault_docs`) still firing on every run; cosmetic cleanup.
> - Linter warnings on the `crete_embeddings` typo (function name) and the `chunks` shadowing in `__main__`.

**Window:** ~~Fri 2026-04-24 → Sun 2026-04-26~~ → **Slipped: Mon 2026-04-27 → Wed 2026-04-29** (3 days, ~2–3 hrs/day). Weekend lost to unplanned family commitments. Friday's chunker work stays banked; Days 1-3 below shift to Mon/Tue/Wed.
**Roadmap tie-in:** [[BBC Industry Intel Platform]] Week 2 — knock-on effect: Week 3 (FastAPI + Docker) shifts from 4/28–5/4 to **4/30–5/4** (compressed from 7 to 5 days). Acceptable because DataQuest Part 4 (FastAPI/Docker conceptual track) can absorb some compression.

**Working agreement update (2026-04-27):** The user writes the AI-engineering code — embeddings batching, Chroma collection design, retrieval pipeline, prompt engineering, eval harness, eval metric math. This is the L3 work the sprint exists to do. The assistant writes only **fiddly string/regex/glue code that the user explicitly delegates** (today's example: YAML-frontmatter stripping, where the user already has working code in another notebook to paste in). Default for everything else: the user writes it; the assistant directs, reviews, and explains Python idioms when they're unfamiliar.
**Inspiration:** Ed Donner LLM Engineering week 5, days 3–5 (`~/llm_engineering/week5/day3.ipynb`, `day4.ipynb`, `day5.ipynb`).

---

## 1. Goal

Take the in-flight beer RAG prototype from `sandbox/RAG_Beer_Intel.ipynb` (notebook) and land it as a **production-shaped Python module structure** with:

1. A clean `beer_rag_app/` package (ingest → retrieve → answer) — no LangChain.
2. A working **Gradio chat interface** hitting the pipeline.
3. An **evaluation package** that measures retrieval *and* answer quality on BBC-relevant test queries, and a Gradio dashboard for the numbers.

The code lives under `~/ai-engineering/sandbox/beer_rag_app/`. End-state is the thing Week 3 of the roadmap wraps in FastAPI + Docker. If you can't wrap it in a module this weekend, Week 3 slips.

---

## 2. Why this matters (Peter's L-levels advanced)

| Area | Now | Target | What this sprint contributes |
|---|---|---|---|
| **RAG Pipelines** | L2 | L3 | End-to-end retrieval + rerank + query-rewrite + eval harness on BBC data is direct L3 evidence. Biggest single jump in this sprint. |
| **Using Primitives** (tokens, embeddings, vectors) | L2→L3 | L3 | Chunk boundaries, embedding choice, similarity math, top-K retrieval — all hand-written, no black-box. |
| **Prompt Engineering** | L2 | L3 | System prompts for QA, rerank ordering, and query rewriting are three distinct structured-output prompts. |
| **Production Concerns** | L1 | L2 | Module boundaries + eval harness is the *mindset* shift from "notebook" to "service." **Not fully closed** — L2 needs the Week 3 FastAPI+Docker step. |
| **AI Stacks — OpenAI** | L1 | L2 | OpenAI embeddings API + structured outputs + LLM-as-judge all exercised. |

What this sprint does **not** move: Training/Running Models (Q4), AI Stacks — Microsoft (Week 4 Azure), Building Agents (no tool-calling yet — scope discipline).

---

## 3. Reference spirit — Ed Donner week 5 days 3–5

Don't re-read the notebooks daily; this is the compression.

**Day 3 — "it works":**
LangChain + Chroma + `HuggingFaceEmbeddings("all-MiniLM-L6-v2")`. Retriever invokes, stuffs docs into a system prompt, `gr.ChatInterface(answer_question).launch()`. The punchline: *"Admit it, you thought RAG would be more complicated."* The spirit we're stealing: **first get the pipeline breathing end-to-end, then worry about quality.**

**Day 4 — "how good is it really?":**
A `Test` pydantic with `question, category, reference_answer, keywords`. 150 tests across 7 categories (`direct_fact, temporal, spanning, comparative, numerical, relationship, holistic`). Two evaluators:
- `RetrievalEval(mrr, ndcg, keyword_coverage)` — purely mechanical, no LLM.
- `AnswerEval(accuracy, completeness, relevance)` — LLM-as-judge, 1–5 scale.
A Gradio dashboard with a button per eval, progress bar, color-coded metric cards, and a per-category bar chart. The spirit: **until you have a number, you are guessing.**

**Day 5 — "go pro":**
Drop LangChain. Native ChromaDB + OpenAI. LLM-driven **semantic chunking** (Pydantic `Chunk { headline, summary, original_text }` generated by LLM from full doc). **Reranking** (LLM reorders top-K by relevance). **Query rewriting** (LLM turns conversational question into a sharp retrieval query). The spirit: **the easy stuff is commodity; the leverage is in document preprocessing + pre/post-retrieval tricks.**

---

## 4. Target module layout

By Sunday night this should be the tree:

```
~/ai-engineering/sandbox/beer_rag_app/
├── ingest.py            # Load vault → LLM-chunk → embed → persist to Chroma
├── answer.py            # Query rewrite → retrieve → rerank → LLM answer
├── app.py               # Gradio ChatInterface
├── evaluation/
│   ├── __init__.py
│   ├── test.py          # Test pydantic + load_tests()
│   ├── eval.py          # evaluate_retrieval, evaluate_answer, evaluate_all_*
│   └── dashboard.py     # Gradio dashboard (from ~/llm_engineering/week5/evaluator.py — adapt, don't copy)
├── vector_db/           # ChromaDB persistent dir (git-ignored)
├── tests.jsonl          # Curated test queries (seed from sandbox/test.jsonl, then BBC-specific)
└── OBSERVATIONS.md      # 5–10 bullets: what numbers showed, which changes mattered
```

Corpus = vault pages (`Notes/*.md`, `Notes/sources/*.md`, `Notes/analyses/*.md`, `Notes/connections/*.md`) per the scaffolding already in `ingest.py:46`. Excludes `Notes/Calmatic/` and `index.md`/`log.md`.

---

## 5. Day-by-day plan

Each day has:
- **Objective** — the sentence that should be true at EOD.
- **Tasks** — ordered. Check off as you finish. Not every task is code; some are reading + thinking.
- **Deliverable** — the concrete artifact that must exist.
- **Checkpoint questions** — if you can't answer these, don't move on.
- **Concepts driven home** — what intuitions this day should cement.

---

### Day 1 — ~~Friday 2026-04-24~~ → carryover Monday 2026-04-27 (~2.5–3 hrs) · "Get it breathing"

**Mirrors:** Ed Donner day 3. Result: a Gradio chat that answers BBC-relevant questions using vault content. Quality is allowed to be bad — that's tomorrow's problem.

**Objective:** `python -m beer_rag_app.app` launches a Gradio chat that retrieves from a persisted Chroma and generates an answer. End-to-end pipeline breathes, no quality bar.

**Tasks:**
- [x] Fix the syntax error at `ingest.py:43` (`class Chunks(BaseModel):\` trailing backslash).
- [x] Decide the **basic-mode chunking strategy** — committed: split on `##`/`###` headings (skip `#` as page title); fall back to 500-char window with 50-char overlap for oversized sections; keep heading as a prefix on each chunk so it biases the embedding toward the section's topic AND gives the LLM anchor context at answer-time.
- [x] Finish `ingest.py`:
  - [x] `split_on_headings(text)` — hand-rolled regex splitter (no LangChain). Handles no-heading docs and text before the first heading. 3/3 sanity tests pass.
  - [x] `char_window(text)` — sliding 500/50 window fallback using `range(0, len(text), step)`.
  - [x] `load_document(path)` — reads a vault file into a `{source, type, text}` dict with type inferred from path.
  - [x] `create_chunks(documents)` — composes split → window → `Result(page_content, metadata)`. Empty-content guard added (drops chunks where `page_content.strip()` is falsy).
  - [x] **YAML-frontmatter strip in `load_document`** — `strip_frontmatter` function with three regex passes: YAML block, wikilink-only opener lines, and named-section drops (Concepts Extracted, Pages Created, Metadata).
  - [x] `create_embeddings(chunks)` — OpenAI `text-embedding-3-small`. Batched at 50 chunks/call (under the 300K-tokens-per-request cap). Dedupe-by-content-hash dict at function entry (drops ~2.3% of chunks that are byte-identical across files). Upsert batched at 5000/call (under Chroma's ~5461 cap).
  - [x] **Chunk IDs:** SHA-256 of `page_content`. Idempotent across reingests, content-drift-detecting.
  - [x] **Reingest semantics:** simplified to "always upsert with content-hash IDs" — same content = same ID = idempotent overwrite. `--reingest` flag deferred (operational TODO; cheap re-embedding makes it not urgent).
  - [x] Persist to `sandbox/beer_rag_app/vector_db/` with collection name `beer_rag`. **6964 vectors** as of 2026-04-27 ingest run.
  - [x] `python sandbox/beer_rag_app/ingest.py` runs cleanly. Prints `1457 docs → 7128 chunks` and `Vector store created with 6964 documents`.
- [x] Write `answer.py` (done 2026-04-28 afternoon):
  - `answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Result]]` — returns answer + chunks for citations / eval / debug visibility.
  - Three functions: `fetch_content` (embed + Chroma top-K), `make_rag_messages` (system+history+user assembly), `answer_question` (composer).
  - Direct OpenAI SDK (not litellm) for v0.1; `MODEL = "gpt-4.1-nano"`, `RETRIEVAL_K = 10`.
  - Shared constants imported from `ingest.py` (`Result`, `DB_NAME`, `EMBEDDING_MODEL`, `COLLECTION_NAME`) — drift-proof.
  - Module-level `openAI` + `vectorstore` + `collection` clients (cold-start cost paid once).
  - **Design decisions resolved (deferred from Day 1):**
    1. Refuse-vs-hedge: **explicit refusal** ("If you do not know the answer say so") encoded in `SYSTEM_PROMPT`.
    2. Citation behavior: **source-tagged context formatting** prepends `f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}"` to every chunk — gives the LLM filenames to cite.
    3. Context formatting: source-tagged, joined with `\n\n`. Picked option 3 from the plan.
    4. `top_k = 10` (slightly above plan's suggestion of 8). Day 2 eval will validate.
  - Smoke-tested: "How can Sam Adams boost sales in 2026" returns coherent answer with relevant chunks; cosine distances 0.63–0.72 (healthy "relevant but varied" spread).
- [ ] Write `app.py`:
  - `gr.ChatInterface(answer_question, title="Beer Industry Intel", type="messages").launch(inbrowser=True)` — adapter needed because `answer_question` returns `(str, list)` but Gradio expects `str`.
- [ ] Run it. Ask ~10 BBC-relevant questions. Note which answers feel obviously wrong. Don't fix anything — write observations in a scratchpad / `OBSERVATIONS.md`.
- [ ] Cleanup before commit: remove debug `print` on `answer.py` line 35.

**Day 1 carryover → Saturday:** embeddings + Chroma persistence + `answer.py` + `app.py` all deferred. Friday was a slower-than-budgeted Python ramp-up day (not a concept problem — the AI-engineering reasoning was strong; Python-idiom friction was the cost driver). Saturday will need a small reshuffle: finish Day 1 carryover in the morning, then compress Day 2 (eval harness) into the afternoon.

**Deferred-to-Day-2 observations from today's work** (seed for `OBSERVATIONS.md`):
- YAML frontmatter at the top of vault files becomes an `('', frontmatter)` chunk with no semantic content. Noise for retrieval. Fix options: strip frontmatter in `load_document`, or drop empty-heading chunks in `create_chunks`. Decide after seeing Day 2 baseline metrics.
- Sanity test for `char_window` initially checked `len(windows) == 3` while two of three windows were actually wrong content. Reinforced: **tests that only check shape, not contents, silently pass while the function is broken.** Same principle scales up to Day 2's eval metrics.

**Deliverable:** Gradio chat running. Screenshot 2–3 example exchanges into `OBSERVATIONS.md` with a "Day 1 impressions" section.

**Checkpoint questions:**
1. What's the difference between `text-embedding-3-small` and `text-embedding-3-large` — dimensionality, cost, and when the larger model actually matters?
2. Why does retrieval use cosine similarity by default in Chroma, and what would change if you switched to L2 distance?
3. What's in your system prompt that would make the model refuse to answer vs. hallucinate?

**Concepts driven home:**
- The full RAG path: **text → chunks → vectors → DB → query → top-K → prompt-stuff → LLM → answer**. You should be able to draw this on a whiteboard after today without looking.
- Why the simplest thing first: any quality improvement needs a baseline to be measured against. No baseline = no measured improvement = no learning.
- Module boundaries = testability. Each of `ingest.py`, `answer.py`, `app.py` does one thing. Production code is not a notebook.

**Common traps to avoid today:**
- Don't start tweaking chunking, reranking, or prompt variants. You have no way to tell if they helped. Tomorrow does.
- Don't import LangChain. The whole point of the `beer_rag_app/` rebuild is to operate closer to primitives. If you reach for LangChain today you've defeated the exercise.
- Don't re-ingest every time. If `vector_db/` already has the collection, skip ingestion unless vault content changed. (Add a `--reingest` flag to `ingest.py` if you want explicit control.)

---

### Day 2 — ~~Saturday 2026-04-25~~ → Tuesday 2026-04-28 (~2.5–3 hrs) · "Measure it"

**Mirrors:** Ed Donner day 4. Result: honest numbers on your Day 1 pipeline.

**Objective:** `python -m beer_rag_app.evaluation.dashboard` launches a Gradio dashboard that runs retrieval eval + answer eval over a curated test set and shows color-coded MRR/nDCG/keyword-coverage + accuracy/completeness/relevance.

**Tasks:**
- [ ] Create `evaluation/` package with `__init__.py`.
- [ ] Write `evaluation/test.py`:
  - `Test` pydantic model: `question: str, category: str, reference_answer: str, keywords: list[str]`.
  - `load_tests() -> list[Test]` reading `tests.jsonl`.
- [ ] Curate `tests.jsonl` with **20–30 test queries about the beer industry + BBC** spread across ≥4 categories (`direct_fact`, `comparative`, `temporal`, `holistic` are the most useful for your corpus). Seed from `sandbox/test.jsonl` if categories match; otherwise write fresh. Categories matter — they let you see **where the pipeline fails**, not just how much.
- [ ] Write `evaluation/eval.py`:
  - `evaluate_retrieval(test: Test) -> RetrievalEval` — run the retriever, compute MRR (rank of first chunk containing a keyword), nDCG@10, keyword coverage (% of test's keywords appearing anywhere in top-K).
  - `evaluate_answer(test: Test) -> AnswerEval` — generate the answer via `answer.answer_question`, send `{question, reference, candidate}` to an LLM judge prompt, parse 1–5 scores for accuracy/completeness/relevance.
  - Generator variants: `evaluate_all_retrieval() -> Iterator[(Test, RetrievalEval, float)]` yielding progress fractions — same signature as `~/llm_engineering/week5/evaluator.py` so the dashboard port is mechanical.
- [ ] Write `evaluation/dashboard.py`:
  - Adapt `~/llm_engineering/week5/evaluator.py`. Change the title, labels, and tests source. Keep the two-button + two-bar-chart layout, color thresholds, and progress bar pattern.
- [ ] Run both evals. Save numbers to `OBSERVATIONS.md` under "Day 2 baseline".

**Deliverable:** `OBSERVATIONS.md` contains **a baseline metrics table** with MRR, nDCG, keyword coverage, and average accuracy/completeness/relevance — plus one paragraph on which category performs worst and a hypothesis why.

**Checkpoint questions:**
1. What does an **MRR of 0.4** tell you vs. **MRR of 0.9**? Where in the pipeline would you look to move each number?
2. **nDCG** rewards relevant docs ranked near the top. What specifically would make nDCG diverge from MRR? Sketch a case.
3. Why is **LLM-as-judge** more reliable for answer quality than exact-match or BLEU? What failure mode of LLM-as-judge do you need to be aware of? (Hint: judge-model bias toward verbose answers.)

**Concepts driven home:**
- **Retrieval eval is deterministic; answer eval is probabilistic.** That's why you separate them — you can improve retrieval and see the MRR move without paying the LLM-judge cost, and you can isolate *answer generation* failures from *retrieval* failures.
- **Test categories are a diagnostic instrument**, not just bookkeeping. A good retrieval pipeline passes `direct_fact` easily and struggles on `spanning` / `holistic`. If the breakdown doesn't match that pattern, something's off.
- The eval harness is your **regression prevention** — from now on, every change to ingest/answer gets graded before you ship.

**Common traps to avoid today:**
- Don't ship an eval with 5 test questions. Below ~20, individual question variance swamps the signal.
- Don't let the LLM judge see more than one answer at a time — comparative judging is a different problem.
- Don't round to 1 decimal and claim "improvement." Keep 3 decimals in `OBSERVATIONS.md`.

---

### Day 3 — ~~Sunday 2026-04-26~~ → Wednesday 2026-04-29 (~2–3 hrs) · "Go pro"

**Mirrors:** Ed Donner day 5. Result: measured improvement (or measured *no* improvement — also valuable).

**Objective:** Add LLM-driven chunking + reranking + query rewriting. Re-run the eval. Compare to Day 2 baseline. Write up what moved and what didn't.

**Tasks:**
- [ ] **Rewrite `ingest.py` chunking** to be LLM-driven:
  - Pydantic `Chunk { headline, summary, original_text }` and `Chunks { chunks: list[Chunk] }`.
  - `make_prompt(document)` instructs the LLM to split with ~25% overlap, returning all three fields per chunk.
  - Parallelize with `multiprocessing.Pool(WORKERS=3)` (already scaffolded in `ingest.py:8`).
  - Re-ingest into a NEW collection (`beer_rag_pro`) so you can diff vs. Day 2. Don't wipe the basic collection.
  - Switch to `text-embedding-3-large` for this run only — one variable to isolate effect.
- [ ] **Add reranking to `answer.py`:**
  - `rerank(question, chunks) -> list[Chunk]` — LLM takes top-K (use K=10–20) and returns reordered IDs via Pydantic `RankOrder { order: list[int] }`.
  - After rerank, keep top 5 for the answer context.
- [ ] **Add query rewriting to `answer.py`:**
  - `rewrite_query(question, history) -> str` — short system prompt asking for a specific, retrieval-optimized rewrite of the user's question.
  - Pipeline: `rewrite → embed → top-K → rerank → top-5 → LLM answer`.
- [ ] Add a config flag at the top of `answer.py`: `MODE = "basic" | "pro"` so the eval can run both without code changes.
- [ ] Re-run eval for **both modes**. Save both result rows to `OBSERVATIONS.md`.
- [ ] Write `OBSERVATIONS.md` Day 3 section (5–10 bullets):
  - Which metric moved most? Which didn't move (or moved backward)?
  - Was it the chunking, the reranking, or the query rewriting? (Run ablations if time allows — disable each one-at-a-time and re-run.)
  - What's the single most surprising number?
  - What's the next experiment you'd run if you had another day? (This is the seed for Week 3.)

**Deliverable:**
- `beer_rag_app/` with basic + pro modes, both evaluable.
- `OBSERVATIONS.md` with baseline table + pro-mode table + one-paragraph narrative of what changed.
- Git commit at EOD: `"Beer RAG: basic + pro pipelines + eval harness"`.

**Checkpoint questions:**
1. **LLM-driven chunking costs real money** (one completion per doc). When does the MRR gain justify it? (Think: static corpus re-ingested monthly vs. streaming corpus re-ingested hourly.)
2. **Reranking** adds latency (one LLM call per query). What's the right K going in — too few and you can't improve, too many and you pay for low-probability candidates? What would your eval tell you?
3. **Query rewriting** helps conversational follow-ups most. Which category in your test set should benefit most — `direct_fact` or `spanning`? Does your data agree?

**Concepts driven home:**
- **The three pro techniques are compositional**: chunking improves retrieval quality, reranking improves retrieval precision given a candidate set, query rewriting improves the candidate set itself. Different levers on different parts of the pipeline.
- **Cost/latency/quality is a 3-way tradeoff.** Each pro technique adds cost and latency. If the eval numbers didn't move enough to justify them, keep the basic mode. Production RAG is measured, not impressive.
- **Ablation is the only honest way to attribute improvement.** "I added three things and the score went up" ≠ "each of three things helped."

**Common traps to avoid today:**
- Don't skip the basic-mode re-run when the pro numbers come in. You need the diff.
- Don't switch embedding model AND add LLM chunking AND add reranking in one go without an ablation plan — you'll learn "something helped" instead of "what helped."
- Don't burn your eval budget. If each LLM-judge call costs $0.005 and you have 30 tests × 2 modes × (maybe) 3 ablations, you're at 180 calls. Fine, but be aware.

---

## 6. After the sprint — where this hands off

This sprint closes the **Week 2 roadmap milestone** (basic-mode RAG + eval baseline). ~~Week 3 (4/28–5/4)~~ **Week 3 (Thu 4/30–Sun 5/4, 5 days)** picks up with:
- **Day 3 carryover (descoped from this sprint):** LLM-driven chunking, reranking, query rewriting, ablations. Lands first in Week 3 — the basic-mode service + clean baseline anchor it.
- **FastAPI wrapper** around `answer.answer_question` exposing a `/query` POST endpoint.
- **Dockerfile** containerizing the service + Chroma.
- DataQuest Part 4 (FastAPI + Docker) as the conceptual track.

**If Wednesday ends without basic mode + a Day 2 baseline, Week 3 slips further.** FastAPI is supposed to wrap *a working evaluated module*, not a mid-build one. Week 3 is now 2 days shorter than originally planned **and** absorbs the Day 3 pro-techniques work — total Week 3 load is dense; flag early if it won't fit and reshape, don't pretend.

**What explicitly does NOT go in this sprint (scope discipline):**
- No FastAPI (Week 3).
- No Docker (Week 3).
- No Azure (Week 4).
- No tool-calling / agents (beyond this 30-day window).
- No Databricks data join (Q2 milestone).
- No fine-tuning (Q4 milestone).

If any of those feel tempting mid-sprint, write them into `OBSERVATIONS.md` under "Deferred ideas" and move on.

---

## 7. Daily log section

Fill in as you go. Future-you will want this when the BBC Intel Platform doc needs a "what happened in week 2" update.

### Fri 2026-04-24
- Start time: ~afternoon
- End time: (in progress)
- Blocks completed: `ingest.py` chunker complete — `split_on_headings`, `char_window`, `load_document`, `create_chunks` all pass sanity tests. Pipeline verified end-to-end on 3 vault docs (15 chunks with `(page_content, source, type, heading)` metadata). Embeddings + Chroma persistence + Gradio chat deferred to Saturday.
- What worked:
  - **Design reasoning** — chunking strategy debate (hybrid headings + char-window fallback, keep heading as semantic prefix), embedding-model tradeoff ("`-small` until there's a reason to upgrade, `-large` as a deliberate Day-3 variable"), and experimental-design discipline (baseline first, isolate variables, ablations) all landed cleanly.
  - **Meta-insight caught in real time** — recognized on own that Python's `=` is a snapshot, not a reactive binding (formula fields in Apex had trained the wrong intuition). That realization is the kind of thing that pays off across every imperative language.
  - **Pushback on bad cadence** — twice flagged when the assistant was dumping code or piling up wall-of-text reviews. Named "I want to write the Python, not read it" and "this is getting lost in noise." Both course-corrections pinned into memory for future sessions.
- What got stuck:
  - **Python idiom ramp-up** was the session's dominant time cost. Not concept confusion — language friction. Specific rough spots: f-string expression behavior (`{m.start()-m.end()}` treated `-` as subtraction), `range()` ergonomics (reached for `while` first), tuple unpacking in for-loops (used `enumerate` where direct unpack was simpler), instance-vs-class in `results.append(Result)`, indentation alignment in a 3-deep nested loop, `\n` vs `\\n` string escapes, slice semantics `text[i:max]` vs `text[i:i+max]`.
  - Each bug was individually small; they compounded because Python muscle memory isn't built yet. See "Areas for more study" in the session review.
- Commit SHA: (commit pending — message: `"Beer RAG Day 1: ingest chunker (split_on_headings, char_window, load_document, create_chunks)"`)

### Sat 2026-04-25 / Sun 2026-04-26 — **No work** (family commitments). Sprint slipped 3 days.

### Mon 2026-04-27 — new Day 1 (carryover, partial)
- Start time: ~afternoon
- End time: ~evening
- Blocks completed: full ingest pipeline through Chroma persistence — `strip_frontmatter`, `create_embeddings` (batched, deduped), batched upsert. End-to-end verified on full vault: **1457 docs → 7128 chunks → 6964 unique vectors persisted to Chroma**. `answer.py` and `app.py` deferred to next session (Day 1 carryover continues).
- What worked:
  - **Plumbing-vs-concept boundary clarified mid-session** — assistant initially over-extrapolated a YAML-strip delegation into "I'll write all plumbing." User correctly pushed back, scope re-cut to "user writes AI-engineering code; assistant writes only explicitly-delegated string/regex glue." Both pinned to memory + plan.
  - **Three-place batching pattern internalized** — `range(0, len(items), step)` with slicing showed up in `char_window`, the OpenAI embeddings loop, and the Chroma upsert loop. Same shape, three different binding constraints (chunk size, OpenAI 300K-tokens-per-request, Chroma ~5461-per-call). User wrote two of the three from spec.
  - **Real-world bug sequence faithfully encountered** — empty page_content from heading-only sections; SHA-256 ID collisions from cross-file boilerplate (`## Source` etc.); both API caps. Each was diagnosed from the error trace and fixed surgically. Production-RAG bugs.
- What got stuck:
  - **Result vs. Chunk class confusion (third recurrence)** — user kept tripping on which Pydantic class has `metadata`. The naming follows Ed Donner's convention but is genuinely ambiguous. Could reduce friction in future sessions by considering a rename (e.g., `RetrievableChunk` for `Result`) — TBD.
  - **Snapshot-vs-binding semantics (second recurrence)** — user re-hit the "value doesn't auto-update when its source changes" bug at the call site for `strip_frontmatter`. Same Apex-formula-fields intuition mismatch as Friday. Worth reinforcing study target.
- Commit SHA: (commit pending — recommended message: `"Beer RAG Day 1 carryover: ingest pipeline through Chroma persistence (1457 docs → 6964 vectors)"`)

### Tue 2026-04-28 — `answer.py` written; Day 1 still NOT closed; Day 2 not started
- Start time: ~midday (Socratic session)
- End time: ~mid-afternoon
- Blocks completed: `answer.py` v0.1 — three functions (`fetch_content`, `make_rag_messages`, `answer_question`) end-to-end. Pipeline breathes against the persisted 6964-vector store. Smoke test answers a real Sam Adams query.
- Blocks NOT completed (slipping into Wednesday): `app.py` Gradio wiring, 10 BBC test questions, `OBSERVATIONS.md` Day 1 impressions, **all of Day 2** (eval harness, tests.jsonl, dashboard, baseline metrics).
- What worked:
  - **Skeleton-first cadence** — empty file → imports → constants → module-level clients → function signatures → bodies one at a time. Each step verified before piling on. User wrote every line of code.
  - **DRY-via-import** decision — refactored `ingest.py` to expose `COLLECTION_NAME` so `answer.py` could import it. User correctly named the principle ("we should import it") before being told the trade-off. This is the kind of SWE intuition that transfers cleanly from Apex.
  - **Tuple return reasoning** — connected `(answer, chunks)` to citation + eval + debug needs the moment it was framed. Saw why throwing chunks away costs Day 2 evaluability.
  - **Message ordering intuition** — got `[system] + history + [user]` right on first guess. Reasoning was directionally correct (model needs context first, then history, then question); deeper reason ("last user message is what the model responds to") added on top.
  - **Identifying the litellm prefix bug** quickly once the 400 came back — connected the `"openai/gpt-4.1-nano"` litellm-format string to the OpenAI SDK rejecting it.
- What got stuck:
  - **Python imports** — confirmed as a real gap (saved to memory `user_python_imports_gap.md`). User did not realize a sibling `.py` file in the same directory is importable without packaging. Apex-orgs auto-resolve names; Python doesn't. Worth dedicated reading: official Python docs on the import system, modules vs packages, `sys.path`. **High-leverage gap to close** — every cross-file reference in Python depends on it.
  - **IDE autocomplete bogus imports — twice in one session** (`from jedi.inference...` and `from sandbox.RAG_Beer_Intel import collection`). PyCharm's "auto-import on type" injects paths that don't actually resolve. Habit to build: glance at imports after typing dunders / cross-module names.
  - **Chroma response shape** — list-of-lists tripped the user multiple times. Tried `results[0]` on a dict (KeyError); double-indexed `results["documents"]` partially; misread bullets inside one chunk as multiple chunks. Concept that needs to land: **`results` is a dict of parallel arrays, where each array's outer `[0]` peels the per-query wrapper.**
  - **`__main__` quoting** — wrote `if __name__ == __main__:` (unquoted). Caused NameError. Apex doesn't need quotes around class name comparisons; Python does for string literals.
  - **Display-truncation misdiagnosis** — `print(s[:300])` was reported as "the system prompt isn't loading completely." Slice is display-only; the underlying string was fine. Worth internalizing that `[:n]` never throws and is always a view, not a transform.
  - **Result-vs-Chunk class confusion (fourth recurrence)** — happened again briefly when discussing what gets returned where. Naming is genuinely ambiguous; consider rename to `RetrievableChunk` once you can make it without breaking smoke tests.
- Concepts driven home today:
  - **RAG embedding-model rule** — same model for ingest and query, else cosine distance is meaningless. Bedrock fact.
  - **Chroma response structure** — `documents`, `metadatas`, `ids`, `distances` are parallel arrays aligned by index. `zip()` is the natural traversal.
  - **Citation anchors via context formatting** — prefixing each chunk with `"Extract from {source}:"` is what *enables* the LLM to cite. Without filenames in the prompt, no citations possible. Also acts as a chunk fence.
  - **Module-level state** — clients (OpenAI, Chroma) opened once at import time, reused across calls. Avoids cold-start cost. Apex parallel: think of these as static-initialized singletons.
- Areas for more study (homework outside session time):
  - Python import system end-to-end: modules, packages, `__init__.py`, `sys.path`, relative vs absolute imports, `if __name__ == "__main__"`. Recommend the *official Python tutorial section 6 (Modules)* — short, authoritative.
  - Python string slicing semantics — `s[:n]`, `s[n:]`, `s[a:b]`, `s[-n:]`, never throws, copy vs view rules.
  - Dict access patterns vs list access patterns — `d[0]` vs `lst[0]` failure modes.
- Commit SHA: (pending — recommended message: `"Beer RAG Day 1 carryover: answer.py v0.1 (fetch_content, make_rag_messages, answer_question)"`)

**Schedule risk — honest pushback:**

Per the plan, Tuesday should have closed Day 1 carryover *and* opened Day 2 baseline. Reality: only `answer.py` got finished. Wednesday now has to absorb:
- Day 1.5: `app.py` + 10 BBC questions + `OBSERVATIONS.md`
- Day 2 entire: `evaluation/` package, `tests.jsonl` curation (20–30 queries), `eval.py` (MRR + nDCG + keyword coverage + LLM judge), `dashboard.py`, run baselines
- Day 3 entire (per current plan): pro pipeline (LLM chunking + reranker + query rewriter), ablations, `OBSERVATIONS.md` write-up

That is **3+ days of work in one ~2–3 hr session**. Not realistic. Three honest options:

1. **Drop Day 3 (pro mode) entirely from this sprint.** Land Day 1+Day 2 cleanly Wednesday. Pro techniques become Week 3 add-ons after FastAPI is up. Cleanest, costs the L3 evidence on rerank/rewrite/LLM-chunking.
2. **Slip Day 3 into Thursday** (Week 3 starts Friday instead of Thursday). Costs another day from FastAPI+Docker (Week 3 was already 7 → 5; would become 4 days, tight but maybe workable if Azure week absorbs).
3. **Compress Day 2 to a minimal eval** (~10 tests, retrieval-only — no LLM judge) so Day 3 still fits Wednesday. Loses answer-quality numbers; retains retrieval signal. Accepts that the eval harness is a stub.

**Recommendation: option 1.** Day 3's pro techniques are a measured-improvement exercise; without a reliable Day 2 baseline (which option 3 weakens), the comparison is meaningless. Better to have a clean basic-mode v1 + honest baseline than a half-broken pro-mode comparison. Pro techniques can land in Week 3 between FastAPI and Docker, where they have a working service to attach to.

Push back on this if you read it differently — e.g., if the L3 evidence on pro techniques is a higher priority than I'm weighting it.

### Wed 2026-04-29 — Day 2 (eval harness + baseline). Day 3 (pro mode) descoped to Week 3.
- Start time:
- End time:
- **Scope this session** (~2–3 hrs): close Day 1 carryover (`app.py` + 10 BBC questions + `OBSERVATIONS.md` Day 1 impressions + `answer.py` line-35 cleanup) → start Day 2 eval harness. If full Day 2 doesn't fit (likely), at minimum land `tests.jsonl` + retrieval eval (`MRR`, `nDCG`, `keyword coverage`); LLM-judge answer eval can slip to Thursday before Week 3 starts.
- Day 2 baseline: MRR=___ nDCG=___ coverage=___% · acc=___/5 comp=___/5 rel=___/5
- Worst category + hypothesis:
- Commit SHA:

### Day 3 — pro mode + ablations — **DESCOPED to Week 3 carryover**
Originally scheduled for Wed 2026-04-29; now lands in Week 3 between FastAPI and Docker if Week 2 closes clean. Rationale: Day 3 is a measured-improvement exercise that needs a working basic pipeline + clean baseline as its anchor. Forcing it into one ~2.5hr Wednesday session would compromise both the baseline and the pro-mode comparison. Better to land basic + honest numbers cleanly, then layer pro techniques onto a deployed FastAPI service in Week 3 where they have a service to attach to. Tasks (LLM-driven chunking, reranking, query rewriting, ablations) preserved verbatim in section 5 above for the Week 3 pickup.

---

## 8. Reference links

- **Roadmap parent:** `~/Documents/Obsidian Vault/Notes/BBC Industry Intel Platform.md`
- **Curriculum index:** `~/Documents/Obsidian Vault/Notes/Learning Curriculum Index.md`
- **Reference notebooks:**
  - `~/llm_engineering/week5/day3.ipynb` — basic RAG + Gradio
  - `~/llm_engineering/week5/day4.ipynb` — eval harness pattern
  - `~/llm_engineering/week5/day5.ipynb` — pro techniques (chunking, rerank, rewrite)
  - `~/llm_engineering/week5/evaluator.py` — dashboard to adapt
- **Live beer-RAG notebook:** `~/ai-engineering/sandbox/RAG_Beer_Intel.ipynb` — reference for what's been explored, not the target artifact
- **Existing scaffold:** `~/ai-engineering/sandbox/beer_rag_app/`
