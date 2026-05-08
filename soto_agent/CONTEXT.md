/# SOTO Agent — Project Context

> Drop-in context recovery doc. Read this first when restarting a session in `/Users/brooksjohnson/ai-engineering/soto_agent/`.

## What is SOTO Agent?

Self-hosted Python agent that wraps multiple BBC data sources (wiki, Databricks, Salesforce) behind one chat surface. Demo target: a Sales Coach in Salesforce LWC that answers rep questions like "How am I tracking on FMB this quarter for accounts X, Y, Z?"

**Name origin:** SOTO = Situation, Objectives, Tools, Objections — the Prepare step of BBC's PRIME selling methodology. Agent's job mirrors the framework: pull situation (SF) → objectives (data) → tools (wiki) → answer.

## Timeline

| Date | Milestone |
|------|-----------|
| **2026-05-20** | Dry run — CTO present. Explainable hallucinations OK. |
| **2026-05-29** | Live demo — possibly COO present. Must be solid. |
| **5/20–5/29** | "Plug-the-embarrassment" window. |

## Architecture decisions (locked this session 2026-05-09)

| Decision | Choice | Reason |
|----------|--------|--------|
| Web framework | **FastAPI** (not Flask) | Async, Pydantic, native SSE for streaming stretch |
| Agent host | **Azure Container App** (not Function App) | No 230s ceiling; agent-loop friendly; future SSE |
| Agent loop | **Self-hosted Python** (not Foundry Agent Service) | Learning value; Ed Donner pattern; full control |
| LLM | **Foundry `gpt-4.1-mini`** | BBC-tenant; compliance-cleared |
| Genie role | **Tool, not primary path** | Demoted 5/8. May call when NL is fuzzy; agent writes direct SQL via Databricks MCP otherwise. A/B eval post-demo. |
| SF round-trip | **Reuse existing Function App + PE channel** | PR 15651 shipped the durable contract — don't rebuild |
| Vocabulary | **3-layer**: system-prompt primer + `glossary_lookup` tool + `wiki_search`/`wiki_read` tools | Cuts tool calls for common terms; precise lookup when needed |
| Streaming UX | **Path A first**: status-step PE → chunked PE (B) → SSE direct (C) | Stay in PR 15651 contract for v1 demo. Agent publishes 2-3 status PEs per query ("searching", "drafting", "done"). Path B/C only if A insufficient. |

## Tools planned (v1, demo-confirmed)

| Tool | Source | Purpose |
|------|--------|---------|
| `wiki_search` | Obsidian vault `Notes/index.md` | LLM-picks up to 8 relevant page paths from index for a question (smart filter, hidden LLM call) |
| `wiki_read` | Obsidian vault `Notes/` | Read a wiki page by name/path; returns body + extracted `[[wikilinks]]`. Outer agent traverses graph via repeated calls. |
| `glossary_lookup` | `/Users/brooksjohnson/BCC_NGST_CG/docs/reference/ubiquitous-language.md` | Precise term definitions, ambiguity resolution |
| `databricks_query` | Brooks-built Databricks MCP (2026-03-11) | SQL queries against BBC data warehouse |
| `salesforce_query` | Apex callout via NGEN-5882 middleware path | Account context (open opps, recent visits, custom fields) |

**Pivot 2026-05-08:** wiki access split from a single `wiki_query` smart tool (Level 2, internal synthesis) → two retrieval primitives `wiki_search` + `wiki_read` (C2 pattern). Outer agent now drives graph traversal through repeated tool calls. Stage 4 synthesis subsumed by outer agent's main response.

**Possible 4th (decision Wed 5/14):** `vector_retrieve` via AI Search w/ semantic ranker. Eval head-to-head vs `wiki_search` on Mon 5/12 first.

## Critical paths — ALWAYS read these before architecture decisions

### Plan + sprint state

- `/Users/brooksjohnson/ai-engineering/current_learning_plan.md` — primary planning doc, top-down read order. Has the 2026-05-08 + 2026-05-09 pivot blocks with full architecture context.
- `/Users/brooksjohnson/Documents/Obsidian Vault/Notes/Calmatic/Global Working Memory.md` — daily working memory, archive blocks
- `/Users/brooksjohnson/Documents/Obsidian Vault/Notes/Calmatic/Active Projects.md` — slot 1 = "BBC Industry Intel Platform — Sales Coach Demo"

### Salesforce-side (durable contract — DO NOT redesign)

- `/Users/brooksjohnson/BCC_NGST_CG/docs/decisions/ADR-0017-async-to-user-via-platform-event-for-ai-integrations.md` — async PE round-trip pattern, correlationId routing, subscriber lifecycle anti-pattern
- `/Users/brooksjohnson/BCC_NGST_CG/docs/decisions/ADR-0018-client-credentials-oauth-inbound-server-to-server.md` — OAuth client_credentials, Connected App, full 10-step per-org deploy runbook, all UAT failure modes
- `/Users/brooksjohnson/BCC_NGST_CG/docs/decisions/diagrams/ngen5884/` — Mermaid sources for both ADRs
- **PR 15651 (merged 2026-05-06)**: shipped Platform Event `Account_Intelligence__e`, Apex `AccountIntelligenceController`, LWC `accountIntelligence`, Connected App `Account_Intelligence_Azure`, Permission Set `Account_Intelligence`, Named Credential `Azure_Account_Intelligence_EC`, External Credential `azure_health_func`. ~1726 LOC.

### Domain vocabulary

- `/Users/brooksjohnson/BCC_NGST_CG/docs/reference/ubiquitous-language.md` — 137-line canonical glossary. **Source of truth for SOTO Agent's vocabulary primer.** Don't copy into vault — read at agent boot.

### Azure middleware (existing infra, sunk-cost win)

- `/Users/brooksjohnson/bbc-sf-middleware/` — Azure Functions v2 Python repo. Entry: `function_app.py`. Endpoints: `GET /health`, `POST /genie`. Has SF OAuth + PE publish + Databricks Genie SDK plumbing.
- `/Users/brooksjohnson/bbc-sf-middleware/CLAUDE.md` — gotcha list (logging vs print, enum equality, port 7071 zombies, etc.)
- `/Users/brooksjohnson/bbc-sf-middleware/models/genie.py` — `GenieResult` Pydantic model
- **Function App deployed:** `sffuncpoc` in `BBC-ITBS-POC-EastUS`, host `sffuncpoc-bne6dsbsfcbpbqbn.eastus-01.azurewebsites.net`

### LLM stack

```
AZURE_OPENAI_ENDPOINT=https://foundry-itbs-poc-2.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_EMBED=text-embedding-3-small
```
Sub: `cebd9dd6-bc18-4e1c-9564-bd4ec13c565b` (BBC DevTest). RG: `BBC-ITBS-POC-EastUS`. Region: East US. Foundry: `Foundry-ITBS-POC-2`.

### Wiki tool source

- `/Users/brooksjohnson/Documents/Obsidian Vault/.claude/commands/wiki-query.md` — the existing `/wiki-query` skill; `soto_agent` ports its primitives (index scan, page reads, link follow) to Python and lets the outer agent drive the loop instead of running it inside one tool
- `/Users/brooksjohnson/Documents/Obsidian Vault/Notes/index.md` — vault index (one-line summary per page); first read on every wiki query
- `/Users/brooksjohnson/Documents/Obsidian Vault/Notes/` — wiki root (concept pages, sources, analyses, connections)

## Round-trip flow (canonical — memorize)

1. User clicks "Ask AI" in LWC. LWC generates `correlationId` UUID.
2. LWC → imperative `@AuraEnabled` Apex (`queryAccountIntelligence(accountId, query, correlationId, conversationId?)`).
3. Apex → callout via Named Credential → POST agent endpoint with payload.
4. Agent does loop work (LLM + tool calls).
5. Agent mints SF token via `client_credentials` against `<org>.my.salesforce.com/services/oauth2/token`.
6. Agent publishes PE `{CorrelationId__c, Status__c: SUCCESS|ERROR, Result__c: JSON | Message__c: error}` via REST `POST /sobjects/Account_Intelligence__e`.
7. PE fires → LWC `empApi` callback → filter by `correlationId` → render.

## Critical config gotchas (already cost time — don't rediscover)

- `SF_INSTANCE_URL` MUST be `<org>.my.salesforce.com`, NOT `lightning.force.com`
- `SF_INSTANCE_URL` value pasted into App Settings = value only, NOT `KEY=VALUE` literal
- Azure App Settings UI has 2-stage commit; prefer `az functionapp config appsettings set` CLI
- `databricks-sdk` is pinned (POC blocker fix); do not auto-bump
- Connected App per-org Consumer Key+Secret minted on first activation; does NOT transfer between orgs
- "Enable Client Credentials Flow" checkbox NOT carried by metadata — manual UI toggle every new org
- Run-As user assignment NOT carried by metadata — manual every new org
- Permission Set assignees NOT carried by metadata — manual every new org
- LWC: subscribe ONCE in `connectedCallback`, never per-click (stacks listeners)
- Python enums ≠ string values; compare `.value` or to enum directly
- `print()` filtered by Functions runtime; use `logging`
- `func start` zombies port 7071: `lsof -ti :7071 | xargs kill -9`

## Open architecture questions (deferred)

| Q | When to decide |
|---|----------------|
| Single PE channel w/ `Source__c` discriminator OR new PE per tool? | When 2nd tool ships SF-side |
| `glossary_lookup` reads file on disk OR loaded into memory at boot? | When building tool |
| Vocabulary primer compression: hand-curate OR LLM-generate from glossary? | Before system prompt v1 |
| Genie space tuning vs raw MCP for direct SQL — which wins on what query types? | Eval Mon 5/12 + post-demo |
| AI Search semantic ranker as 4th tool? | Wed 5/14 (after wiki vs AI Search eval) |
| Path B (chunked PE per sentence) needed, or does Path A suffice? | After 5/20 dry-run feedback |
| Path C (SSE direct LWC ↔ Container App)? | Post-demo. New CSP Trusted Site + auth model. |

## Build order locked

1. **Wiki primitives** — `wiki_search` + `wiki_read` in `tools/wiki.py`, plain Python, notebook-testable, NO FastAPI yet ✅ done 2026-05-08
2. **Vocabulary primer** — compress `ubiquitous-language.md` to ~600-token system-prompt block
3. **Agent loop skeleton** — `soto_agent/app.py` with system prompt, tool registration, run loop. **Wiki graph traversal lives here** (per C2 pivot).
4. **Glue tools to loop** — `wiki_search`/`wiki_read`, `glossary_lookup` first; `databricks_query`, `salesforce_query` next
5. **FastAPI route** — wrap loop as `POST /soto-agent` (or similar)
6. **Azure deploy** — Container App
7. **SF integration** — new Named Credential URL pointing at agent route; Apex/LWC reuse existing PR 15651 contract

## Repo layout (target)

```
/Users/brooksjohnson/ai-engineering/soto_agent/
├── __init__.py
├── app.py                    # FastAPI + agent loop entry
├── tools/
│   ├── __init__.py
│   ├── wiki.py               # wiki_search + wiki_read primitives (build first)
│   ├── glossary_lookup.py
│   ├── databricks_query.py
│   └── salesforce_query.py
├── prompts/
│   └── system_prompt.md      # vocabulary primer + agent instructions
├── CONTEXT.md                # this file
└── README.md
```

## Anti-goals (explicitly not doing for v1)

- LangChain / LangGraph / Crew / AutoGen frameworks — DEFERRED to post-5/29 per 2026-05-08 plan pivot
- Foundry Agent Service hosting — DEFERRED; A/B comparison post-demo
- SSE-direct streaming (Path C) — DEFERRED post-demo. Status-step PE (Path A) in scope for 5/29; chunked PE (Path B) only if A insufficient.
- Vector RAG (`vector_retrieve` via AI Search) — Option B only; decision 5/14
- New Salesforce metadata — reuse PR 15651 artifacts; new endpoint = new Named Credential URL only
- ECA migration (Connected App → External Client App) — production hardening, post-demo

## Learning posture (per `current_learning_plan.md`)

- Pricer Wk 6 — PAUSED 5/6 → 5/30. Resume after demo.
- Ed Donner Agent Course — 1_foundations → 2_openai → 6_mcp (week of 5/19). Frameworks deferred.
- Chip Huyen Ch 6 RAG/Agents — finish Sat 5/10.
- Passive LangChain/LangGraph video viewing OK; do NOT refactor demo code into framework before 5/29.
