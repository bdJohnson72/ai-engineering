# Current Learning Plan — Beer RAG (ongoing) + Pricer Skill Build

> **Session restart pointer (last updated 2026-05-12):** If restarting, read in this order: (1) `soto_agent/CONTEXT.md` "Where we left off (end of 2026-05-12)" — most current state of the demo build, (2) the new 2026-05-12 status block at the very top of this plan (immediately below), (3) `.claude/sessions/2026-05-12-1531-soto-agent-glossary-fastapi-acr.md` for the day's learnings + compound review, (4) older pivot blocks for context (2026-05-08, 2026-05-06, etc. — all preserved below), (5) `~/Documents/Obsidian Vault/Notes/Calmatic/Active Projects.md` slot 1 ("BBC Industry Intel Platform — Sales Coach Demo"), (6) `~/Documents/Obsidian Vault/Notes/Calmatic/Global Working Memory.md` for daily working memory.

> **STATUS 2026-05-12 EOD — steps 1-5 done + first ACR image pushed. Container App next.**
>
> The agent has been built up incrementally over Sat 5/9 → Tue 5/12. End-of-Tuesday state:
> - **Step 1 ✅ Wiki primitives** (`wiki_search`/`wiki_read`). Patched today after a selector-LLM hallucination ("Entities/" folder prefix) returned an empty page; selector prompt hardened + basename rglob fallback added.
> - **Step 2 ✅ Vocabulary primer** (`prompts/system_prompt.md`, ~1.5K tokens after disambiguation/comparison/efficiency rule additions).
> - **Step 3 ✅ Agent loop skeleton** (`app.py` with model registry, tool dispatch, MAX_TURNS=20).
> - **Step 4a ✅ `glossary_lookup`** (today). Parses `BCC_NGST_CG/docs/reference/ubiquitous-language.md` at import; 55 canonical + 7 ambiguities; merges canonical+ambiguity on overlap (e.g. "Promotion"). First pytest file in the repo (`soto_agent/tests/test_glossary_lookup.py`), 19 cases, all green.
> - **Step 4b ⬜ `databricks_query`** — Wed 5/13 afternoon (after deploy spine).
> - **Step 4c ⬜ `salesforce_query`** — Thu-Fri.
> - **Step 5 ✅ FastAPI route** (today). `soto_agent/server.py` POST /soto-agent. Sync `def` route, Pydantic body, `logger.exception` on error. Needs `/health` added Wed AM for Container App probes.
> - **Step 6a ✅ Dockerfile + slim deps + Makefile.** Image `bbcsotoacr.azurecr.io/soto-agent:latest` built via `az acr build` (37s).
> - **Step 6b ⬜ `az containerapp create`** — Wed 5/13. Secrets + env vars + ingress=external + port=8000.
> - **Step 7 ⬜ SF Named Credential URL swap** — Wed 5/13 PM, after 6b returns an FQDN.
>
> **New today, supporting infra (not in original plan):**
> - `soto_agent/scripts/build_vault_subset.py` — denylist-based filter of the user's local Obsidian vault into `soto_agent/data/vault/` (1600 .md files, 6.1 MiB). Filters `index.md` rows in place to preserve hand-curated summaries; deny patterns scoped to personal/AI-eng content. Output is gitignored (build artifact).
> - `soto_agent/Makefile` — `test`, `refresh-glossary`, `vault`, `prep`, `image`, `deploy`, `run`, `clean`. Wraps the full build flow so prep can't be forgotten before `az acr build`.
> - `soto_agent/data/ubiquitous-language.md` — committed copy of the BBC glossary. `make refresh-glossary` syncs from BCC_NGST_CG when SF team updates the source.
>
> **Gotchas saved as memory today:**
> - `az acr build --file <path>` is **cwd-relative, not context-relative.** Makefile must `cd` to context dir or build fails with "Unable to find Dockerfile." Saved at `insight_az_acr_build_file_path.md`.
> - User flagged Python testing as a learning-plan gap. Saved at `user_python_testing_gap.md`. Add a pytest block to the post-demo learning posture (likely Week 2-3 post 5/30 when Pricer Wk 6 resumes).
>
> **Demo timeline reaffirmed:**
> - Wed 5/13: containerapp create + SF integration spine (LWC reaches live agent — wiki + glossary only).
> - Thu-Fri: `databricks_query` + `salesforce_query` tools wired into the deployed agent.
> - Sat-Sun 5/16-17: buffer / refinements.
> - Tue 5/19: pre-demo dry run.
> - **Wed 5/20: CTO dry run.** Explainable hallucinations OK.
> - **Fri 5/29: live demo (possibly COO).** Must be solid.
>
> **v2 plan (post-5/29):** Mosaic AI Agent Framework on Databricks. **Its own repo** — not this monorepo. User confirmed today that `ai-engineering/` is a learning monorepo with unrelated torch/transformers/langchain in `pyproject.toml`; v2 starts with a clean dep tree. Memory at `project_soto_v2_databricks.md`.
>
> **Learning track posture through 5/29 (unchanged):**
> - Pricer Wk 6 — paused 5/6 → 5/30. Resume after demo.
> - Ed Donner Agent Course — 1_foundations active, then 2_openai, then 6_mcp (week of 5/19). Frameworks deferred.
> - LangChain/LangGraph passive viewing OK; do NOT refactor demo code into framework before 5/29.

> **PIVOT 2026-05-08 — Sales Coach demo + 3-tool agent + wiki primary retrieval.** Peter demo review Thu 5/8 PM revealed: **dry run 5/20 with CTO present, live demo 5/29 possibly with COO present.** Stakes higher than expected. Brooks confirmed BBC has formal permission to pass company data to Azure-hosted LLMs (Foundry) — compliance fully unblocked. Demo positioning locked as **Sales Coach application** (rep-facing assistant, but cross-business uses obvious).
>
> **Architecture rethink (driven by Brooks pushback during 5/8 shutdown):**
> - **Wiki tool stays primary retrieval tier.** Per `feedback_structured_wiki_beats_chunk_rag.md` 2026-05-06: LLM reading wiki + following wikilinks consistently beats chunked RAG retrieval in Brooks's hands. Holds even though Brooks hasn't yet tried query rewriting / rerankers / AI Search semantic ranker.
> - **Genie demoted to fallback.** Genie was originally just plumbing test (NL→SQL on a curated subset). With agents + Databricks MCP via Unity Catalog, agent has full schema access. Genie middleware retained for SF write-back use cases (NGEN-5882/5884 PE plumbing not wasted) but no longer primary agent retrieval tool.
> - **Salesforce becomes 3rd data source.** Account context (open opps, recent visits, custom fields) lives only in SF. Demo path: Apex callout via existing NGEN-5882 middleware (sunk-cost win). Production path: dedicated SF data MCP, post-demo.
>
> **Demo v1 (5/29) — 3 confirmed tools:**
> 1. `wiki_query` — wraps existing `/wiki-query` skill workflow as Python + FastAPI endpoint. Reads `Notes/index.md` → LLM picks pages → reads pages → LLM synthesizes answer. **TODAY 5/9 critical path build.**
> 2. `databricks_query` via MCP — Brooks-built Databricks MCP from 2026-03-11. Eval Mon 5/12 (5 representative sales questions). Fallback if hallucination >20%: wrap Genie inside MCP path as guardrail.
> 3. `salesforce_query` — Apex callout via NGEN-5882 middleware path for demo. Returns structured account context.
>
> **Possible 4th tool (decision Wed 5/14):** `vector_retrieve` via AI Search w/ semantic ranker. AI Search demoted to **Option B** — eval head-to-head vs wiki Mon 5/12. Add only if eval shows lift over wiki on specific query types. AI Search resource provisioned 5/8; `ingest_aisearch.py` work continues but lower priority than wiki_tool.
>
> **UX direction — streaming LWC vs PE round-trip:** Existing PE round-trip path (~6-15s silent wait) bad for chat UX. Brooks proposed direct LWC → Container App SSE streaming, skipping Apex/PE for chat. Auth via short-lived JWT minted by Apex once-per-session. **Stretch for 5/29 demo if Sat 5/10 v1 deploy lands clean; else post-demo polish.** Rule that emerged: PE plumbing for "agent writes back to SF" use cases (async, audit-trail). Direct streaming for "user chats with agent" (sync-feeling, sub-second). Same agent, two surface areas.
>
> **5/20 dry run vs 5/29 live posture:** Dry run = explainable hallucinations OK. Live = must be solid. 9 days between = the plug-the-embarrassment window.
>
> **Sales Coach demo narrative locked:**
> > "Rep asks 'How am I tracking on FMB this quarter for these 3 accounts?' Agent pulls account info from SF, pulls volume data from Databricks, pulls Twisted Tea launch context from internal wiki, composes the coaching answer. Streamed live to LWC."
>
> **Time budget revised:** "company priority + extra time over next couple weeks" = ~22-28h/week available (up from prior ~16-18h). Salesforce sprint overhead presumed reduced. Buys breathing room for AI Search eval + LWC streaming spike.
>
> **Learning track posture through 5/29:**
> - Pricer Wk 6 — PAUSED 5/6 → 5/30 (re-confirmed 5/8). Resume after demo.
> - Ed Donner Agent Course — 1_foundations active, then 2_openai, then 6_mcp (week of 5/19). Frameworks (3_crew, 4_langgraph, 5_autogen) DEFERRED to post-5/29. **LangChain/LangGraph study explicitly deferred** per 5/8 conversation — direct-API agent first, frameworks as A/B comparison post-demo.
> - Chip Huyen Ch 6 RAG/Agents — finish Sat 5/10.
> - Passive Ed Donner LangChain/LangGraph video viewing on the side OK; do NOT refactor demo code into framework before 5/29.
>
> **Brooks's new working dir (2026-05-09):** Brooks created `~/ai-engineering/BBC demo/` (or similar — confirm name; spaces in dir names cause Python import issues, suggest renaming to `bbc_demo/` if confirmed). This may become primary build dir, possibly replacing or supplementing `sandbox/beer_rag_app/`. Confirm intent at next session restart.
>
> **Revised deployment names + endpoints (carry-forward):**
> ```
> AZURE_OPENAI_ENDPOINT=https://foundry-itbs-poc-2.cognitiveservices.azure.com/
> AZURE_OPENAI_API_VERSION=2024-12-01-preview
> AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4.1-mini
> AZURE_OPENAI_DEPLOYMENT_EMBED=text-embedding-3-small
> AZURE_SEARCH_ENDPOINT=<TBD — Brooks provisioned 5/8>
> AZURE_SEARCH_INDEX=beer-rag-v1
> ```
> Sub: `cebd9dd6-bc18-4e1c-9564-bd4ec13c565b` (BBC DevTest). RG: `BBC-ITBS-POC-EastUS`. Region: East US. Foundry resource: `Foundry-ITBS-POC-2`.
>
> **Existing infrastructure pointer — `bbc-sf-middleware` (added 2026-05-09):**
> - **Repo:** `~/bbc-sf-middleware` — Azure Functions v2, Python programming model. Entry: `function_app.py`. Decorator-based (`@app.route(...)`); no `function.json` files.
> - **What it does today:** SF → Azure Function → Databricks Genie API, with response returned **asynchronously** to SF via Platform Event `Account_Intelligence__e` (correlation ID threads the round trip). NGEN-5882/5884 closed; this is the production Genie path.
> - **Endpoints:** `GET /health`, `POST /genie`. `/genie` body fields: `accountName, accountId, iStoreNumber, query, correlationId, conversationId?` (last is optional — present for multi-turn Genie history). Response: HTTP 200 with `{correlationId, status, result}` AND a Platform Event publish containing `CorrelationId__c, Status__c, Result__c` (or `Message__c` on error).
> - **Inbound auth:** Function-level API key (`AuthLevel.FUNCTION`). **Outbound auth (Function → SF):** OAuth client credentials flow against `SF_INSTANCE_URL/services/oauth2/token` (Connected App).
> - **Genie execution flow:** Databricks SDK `WorkspaceClient` → `genie.start_conversation` (or `genie.create_message` for follow-up turn) → `wait.result(timeout=120s)` → if SQL returned, `execute_message_query` then poll `statement_execution.get_statement` until `SUCCEEDED/FAILED/CANCELED/CLOSED`. Hard caps: 60s SQL exec timeout, 50-row PE payload cap, 230s Azure HTTP function ceiling.
> - **Env vars expected:** `SF_INSTANCE_URL, SF_CLIENT_ID, SF_CLIENT_SECRET, DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_GENIE_SPACE_ID`.
> - **Result model:** `models/genie.py::GenieResult` — pydantic; carries `sql_query`, `columns`, `rows`, plus Genie's clarification text. Serialized to JSON for the PE `Result__c` field.
> - **Implication for `soto_agent` (the new dir, this week's build):** This middleware is the SF↔Azure transport for the **Genie tool**, not for the wiki tool. Open architecture question for 5/10–5/12: does `wiki_query` route through this Function App (add a new `@app.route("wiki-query")` alongside `genie`, reuse PE plumbing) OR live in a separate FastAPI Container App (per 5/4 + 5/8 pivots)? Container App wins for streaming stretch (SSE) + agent-loop length, but adds a second deploy surface. Decision deferred to first session after `wiki_query` route works locally.
> - **Sunk-cost win:** PE round-trip path already operational. Even if "user-chats-with-agent" surface goes direct LWC→Container App SSE, "agent-writes-back-to-SF" surface stays on this PE path. The two-surface rule from the 5/8 pivot lines up cleanly with what's already deployed.
>
> **Repo gotchas to respect (from `bbc-sf-middleware/CLAUDE.md`):** `print()` is filtered — use `logging`. Python enums ≠ their string values (compare `.value`). Prefer SDK `Wait.result()` over hand-rolled poll loops. `func start` zombies port 7071 — `lsof -ti :7071 | xargs kill -9` before restart. Databricks PATs need explicit Genie scope.
>
> **Salesforce-side durable contract (added 2026-05-09 — shipped in PR 15651, branch `docs/ngen5884-adrs`):**
> - **ADRs that govern this:** `BCC_NGST_CG/docs/decisions/ADR-0017-async-to-user-via-platform-event-for-ai-integrations.md` + `ADR-0018-client-credentials-oauth-inbound-server-to-server.md`. Both `Status: Accepted` 2026-05-05. Treat these as the canonical pattern for ALL future AI integrations (wiki tool, vector retrieve, multi-tool agent — all follow this).
> - **The SF surface is durable; the Azure side is what may move.** Whether `soto_agent` lives in the existing Function App (`sffuncpoc`) or a new Container App, the Salesforce contract stays the same.
>
> **Salesforce metadata shipped (PR 15651, ~1726 LOC across 19 files):**
> - **Platform Event:** `Account_Intelligence__e` — fields `CorrelationId__c` (UUID, caller-generated in LWC), `Status__c` (`SUCCESS|ERROR`), `Result__c` (32 KB long-text JSON payload), `Message__c` (error text). 24-hour PE retention. Reusable channel — future AI integrations can extend `Result__c` schema OR create new PEs following the same shape.
> - **Apex:** `AccountIntelligenceController.queryAccountIntelligence(accountId, query, correlationId, conversationId)` — 4-arg @AuraEnabled method. First-turn Apex enriches with account context (`iStoreNumber`); continuation turns skip enrichment (Genie remembers via `conversation_id`). Fire-and-forget callout — response body unused; PE delivers the answer.
> - **LWC:** `accountIntelligence` (HTML/JS bundle). Subscribes to PE channel ONCE in `connectedCallback`, unsubscribes in `disconnectedCallback`, filters incoming events by `correlationId`. 2-minute client-side timeout w/ Retry button. Inline error rendering — no toasts. **Critical anti-pattern fixed in 5/4 dev:** subscribing inside `handleClick` stacked listeners → duplicate transcript entries; same class as NGEN-5777 anti-double-DML lesson. `/lwc-tdd` REVIEW phase now checks for it.
> - **Connected App:** `Account_Intelligence_Azure` — `client_credentials` grant. Runs as designated user (POC: `brooks.johnson@bostonbeer.com.<sandbox>`; production: dedicated integration user). Per-org Consumer Key + Secret minted on first activation — does NOT transfer between orgs. ECA migration deferred (production hardening).
> - **Named Credential:** `Azure_Account_Intelligence_EC` (URL = Function host + `?code=<host-key>`).
> - **External Credential:** `azure_health_func`.
> - **Permission Set:** `Account_Intelligence` — grants Create on PE + field-level access. Must be assigned to run-as user per-org (does NOT carry through metadata).
> - **Function App:** `sffuncpoc` in `BBC-ITBS-POC-EastUS`, host `sffuncpoc-bne6dsbsfcbpbqbn.eastus-01.azurewebsites.net`, route `/api/genie`. Python 3.13.
>
> **Round-trip flow (canonical — memorize):**
> 1. User clicks "Ask AI" in LWC. LWC generates `correlationId` UUID.
> 2. LWC → imperative `@AuraEnabled` Apex (`queryAccountIntelligence`).
> 3. Apex → callout via Named Credential → `POST /api/genie` with `{accountName, accountId, iStoreNumber, query, correlationId, conversationId?}`. Apex callout cap = 120s; uses fire-and-forget contract.
> 4. Function does Genie work (start_conversation OR create_message → execute_message_query → poll statement_execution).
> 5. Function mints SF token via `client_credentials` against `<org>.my.salesforce.com/services/oauth2/token`.
> 6. Function publishes PE `{CorrelationId__c, Status__c: SUCCESS, Result__c: GenieResult JSON}` (or `Status__c: ERROR, Message__c: ...`) via REST `POST /sobjects/Account_Intelligence__e`.
> 7. PE fires → LWC's empApi callback → filter by `correlationId` → render datatable + transcript.
>
> **Per-org deploy NOT carried by metadata (manual every new org — full 10-step runbook in ADR-0018):**
> 1. Confirm Connected App deployed (SOQL `ConnectedApplication`).
> 2. **Tick "Enable Client Credentials Flow"** in App Manager → app → View → Edit (the metadata XML doesn't carry this checkbox).
> 3. Set Permitted Users = "Admin approved users are pre-authorized".
> 4. Set Run-As user (Client Credentials Flow section appears only after step 2).
> 5. Assign Permission Set: `sf org assign permset -n Account_Intelligence -o <user>`.
> 6. Add Permission Set to Connected App's allowed list.
> 7. Update Azure App Settings with **NEW per-org Consumer Key + Secret** via `az functionapp config appsettings set` (UI two-stage commit drops values).
> 8. **Force-recycle** Function workers: `az functionapp stop && start` (graceful restart leaves cached env vars in mid-flight workers).
> 9. Update Named Credential URL with current Azure host key (`az functionapp keys list --query "functionKeys.default"`).
> 10. Smoke test: curl token mint, then click "Ask AI" in LWC.
>
> **Critical config gotchas seared into the runbook:**
> - `SF_INSTANCE_URL` MUST be `<org>.my.salesforce.com` (API host), NOT `lightning.force.com` (UI host). UI host triggers cross-host redirect → `requests` mangles POST body → `unsupported_grant_type` 400.
> - `SF_INSTANCE_URL` value pasted into App Settings = value only, NOT `KEY=VALUE` literal (causes `InvalidSchema: No connection adapters found`).
> - Azure App Settings UI has a two-stage commit (pane Apply + page Apply); always prefer `az` CLI to bypass.
> - `databricks-sdk` is pinned (POC blocker fix); do not auto-bump.
>
> **Domain vocabulary source — `BCC_NGST_CG/docs/reference/ubiquitous-language.md` (added 2026-05-09):**
> - 137-line canonical glossary of BBC business terms (RO, MOB, COT Priority, Chain Mandate, Smart Rec, PRIME, SOTO, B.A.S.E., Three-Tier, Customer Set, Anchor Account, etc.) with mappings to Salesforce object API names. Includes 4-source RO breakdown, 8 Retailer Template Prefixes, 7 flagged ambiguities ("Objective", "Promotion", "Survey", etc.).
> - **SOTO is defined here** — Situation/Objectives/Tools/Objections; the **Prepare** step of PRIME. Agent dir name `soto_agent/` matches.
> - **Agent integration plan (3 layers):**
>   - **System prompt seed:** compress ~30 most common terms into ~600-token vocabulary primer; always loaded; prompt-cache makes it ~free after first call. Cuts a tool call for common questions.
>   - **`glossary_lookup` tool:** exposes full file contents for precise lookups when agent senses ambiguity.
>   - **`wiki_query` tool:** stays the primary synthesis/multi-page tool; glossary handles vocabulary, wiki handles knowledge.
> - **File ownership:** read directly from `BCC_NGST_CG/docs/reference/ubiquitous-language.md` at agent boot. Don't copy into vault — single source of truth (the SF team reviews/owns it). Acceptable interim: symlink into `Notes/` if filesystem access from agent host is awkward in v1.
>
> **Implication for `soto_agent` (this week's build):** When `wiki_query` and the agent loop need to surface in Salesforce, the path is **not new SF metadata** — it's reusing this contract. Two options:
> - **Reuse `Account_Intelligence__e` PE** with a `Source__c` discriminator added — single channel, multi-tool. Cheapest.
> - **New PE per tool** (`Wiki_Query__e`, `Soto_Agent__e`) — cleaner schema separation but more metadata to deploy per-org. Deferred decision.
> Either way: the durable SF artifacts (Apex callout pattern, LWC subscribe pattern, Connected App, Permission Set, Named Credential URL) are the template. Don't redesign them. If `soto_agent` ends up in a new Container App rather than the existing Function App, that's an Azure-side change only — the SF-side `AccountIntelligenceController` (or its sibling) just calls a different endpoint URL via a new Named Credential. Auth flow + PE channel + correlationId routing all stay.



> **PIVOT 2026-05-06 — Foundry stack + AI Search migration replaces self-hosted RAG plumbing.** Tue AM Azure portal investigation found `Foundry-ITBS-POC-2` already deployed in `BBC-ITBS-POC-EastUS` RG with Brooks holding Contributor inherited. Deployed `gpt-4.1-mini` (chat) + `text-embedding-3-small` (embeddings) — first AI Capability Center models on BBC infra. Compliance constraint (no direct openai.com calls with BBC data) is now resolved: all production LLM calls route through Foundry endpoint inside BBC tenant.
>
> **Architecture consequence:** v0/v1 deploy split dropped. Sat 5/10 ships **v1 with BBC vault data on real Foundry stack** (Container App + AI Search + Genie + `gpt-4.1-mini`). Standalone rewriter/reranker work folds into AI Search semantic ranker (built-in). Tue PM = Foundry orientation + Playground hands-on (Path A). Wed = AI Search provisioning + corpus migration (`ingest_aisearch.py`). Thu = `agent.py` skeleton using `AzureOpenAI` client + AI Search retrieval + Genie httpx. Fri = pricer Wk6 Day 3 (optional Foundry fine-tune pivot) + FastAPI wrap. Sat = Container App deploy.
>
> **Foundry as learning substrate (added 5/6):** Brooks committed to using Foundry as the place to apply growing skills — agents, fine-tuning, evals, indexes all live there. Ed Donner / Chip Huyen / DataQuest still teach the *why* (mechanics + intuition); Foundry is the *where* (BBC production stack). Each major code-pattern learned in Ed Donner gets a "how would I do this in Foundry" follow-up exercise.
>
> **Deployment names + endpoints (paste-ready):**
> ```
> AZURE_OPENAI_ENDPOINT=https://foundry-itbs-poc-2.cognitiveservices.azure.com/
> AZURE_OPENAI_API_VERSION=2024-12-01-preview
> AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4.1-mini
> AZURE_OPENAI_DEPLOYMENT_EMBED=text-embedding-3-small  # adjust if deployment named differently
> ```
> Sub: `cebd9dd6-bc18-4e1c-9564-bd4ec13c565b` (BBC DevTest). RG: `BBC-ITBS-POC-EastUS`. Region: East US. Foundry resource: `Foundry-ITBS-POC-2`.

> **PIVOT 2026-05-04 — Agentic-RAG MVP + Azure deploy substrate.** Architecture target shifts from "iterate retrieval quality on the vector RAG" to "agentic RAG running on Azure with two tools." Vector RAG (beer_rag_app) is no longer the answer; it becomes one tool inside an agent. Genie (via NGEN-5882/5884 middleware, now closed) is the second tool. Agent decides which to call. **The 4-row rewriter/reranker comparison table is dropped as a sprint deliverable** — rewriter + reranker fold into `vector_retrieve` as internal LLM helpers (Ed Donner Wk5 Day 5 pattern) so the wiki tool's quality is sharper before the agent wraps it. The understanding-it-deeply track for retrieval moves to Q3 with real demo questions.
>
> **LLM compliance constraint:** BBC policy forbids direct calls to public OpenAI/Anthropic APIs with company data. Production LLM must be Azure OpenAI Service (BBC-tenant-scoped, Microsoft-operated, contractually no training on inputs). Local dev stays on direct `OpenAI` client with synthetic/public data only. Code uses a `get_llm_client()` factory so the swap is one line. Mon 5/5 investigation: portal check + Mike Lavy DM + pricing math → email Peter / IT with facts. Self-serve / 1-week / procurement-event are the three timeline branches.
>
> **Deploy substrate decision:** Azure Container App + FastAPI, NOT Azure Function. Reasons: agent tool-call loops are stateful-ish and longer than Function time limits; Container Apps scale to zero; same Docker image runs locally for dev. DataQuest has FastAPI + Docker section — added to this week as Wed-Thu train reading.
>
> **v0 vs. v1 deploy:**
> - **v0 (target Sat 5/10):** Container App on Azure with synthetic/public data, direct OpenAI API. Proves architecture end-to-end. **No BBC vault data.**
> - **v1 (TBD by 5/16-5/24):** Same architecture, swap to Azure OpenAI client + BBC vault data once procurement clears.
>
> **PIVOT 2026-05-01 (still applies) — Two parallel tracks:**
> - **Track P (pricer skill build)** — Ed Donner LLM Engineering Wk 6 day1-5 spread over 2 weeks. Fine-tuning mechanics on a non-BBC dataset. Skill acquisition for the eventual BBC fine-tune step.
> - **Track B (Beer Intel app — ongoing)** — beer_rag_app continues. Now reframed as "build agent that uses beer_rag_app as a tool." Demo-able Azure-hosted artifact target ~5/10 (v0) and ~5/16-5/24 (v1).
> - **AI Stacks L-credentials deprioritized** per 2026-05-01 user feedback. Real capability framing only.
>
> **Where we are (end of Sun 2026-05-03):** Track B Days 1-2 shipped (ingest.py + answer.py + app.py + evals/evaluation.py). Day 3 NOT shipped — Sat was study-shaped not sprint-shaped. State on disk:
> - `beer_rag_app/ingest.py` — full pipeline working: 1457 docs → 7128 chunks → 6964 vectors in Chroma `beer_rag` at `sandbox/beer_rag_app/vector_db/`.
> - `beer_rag_app/answer.py` — query flow: `fetch_content` → `make_rag_messages` → `answer_question`. v0.1 smoke-tested.
> - `beer_rag_app/app.py` — Gradio chat wired through `answer_question`. Title "Beer-O-Matic".
> - `beer_rag_app/evals/evaluation.py` — `TestQuestion` Pydantic + `load_tests` + retrieval metrics + `run_baseline()` + real `evaluate_retrieval` calling `fetch_content`.
> - `beer_rag_app/test.jsonl` — 100 curated test queries.
> - **Day 2 baseline run NOT yet executed.** Code shipped 4/30, run still pending. Optional now under new plan — only do if it informs `vector_retrieve` decisions.
> - **Track P:** Wk6 Day 1 video watched 5/3. Day 1 notebook (`~/llm_engineering/week6/day1.ipynb`) NOT yet run. Day 2 (Mon 5/5) presumes Day 1 ran — may need to run Day 1 first thing Mon if not done.
> - Middleware (NGEN-5882 + 5884): SF→Azure→Genie→SF round-trip plumbing CLOSED 5/1. Currently ships a canned prompt; Mon task swaps to plain-text query param.
> - DataQuest decorators ~done. Inbox carry-forward: `functools.wraps` lesson Mon 5/5.
>
> **Immediate handoff state for Monday 2026-05-05:** Home day. Six items in priority order:
> 1. **Azure OpenAI investigation** (60m total) — portal Subscriptions + Resource Providers (Microsoft.CognitiveServices) check, Mike Lavy Slack DM about AI Foundry status, pricing-calculator math for demo-scale usage. Document findings.
> 2. **Genie plain-text query feature** (60m) — middleware: PE payload schema gets `{query}` field, Pydantic validates, Genie call uses incoming text. Apex test from local sandbox.
> 3. **Wk6 Day 2 pricer dataset shaping** (90m) — `~/llm_engineering/week6/day2.ipynb`. If Day 1 not yet run, run Day 1 first.
> 4. **Decorators close** (30m) — `functools.wraps` lesson.
> 5. **Email Peter / IT** (15m, defer to Tue if Mon investigation incomplete) — Azure OpenAI access path with Mon's findings.
> 6. **Read for Tue train** (no Mon time required) — OpenAI tool-calling guide bookmarked for Tue commute.
>
> **Operational TODOs flagged but deferred:**
> - Re-running `ingest.py` currently re-embeds the whole corpus (~$0.02 each run). Add `--reingest` flag gating later if iteration cost becomes annoying. Note: when v0 deploys to Azure, Container App will need to either (a) bake vector_db into image, (b) mount volume, or (c) re-ingest at boot — design decision for Sat 5/10.
> - `crete_embeddings` typo (function name) — fix when next touching ingest.py (Wed 5/7 when wrapping `vector_retrieve`).
> - Mutable default arg `history=[]` in `answer.py` — fix to `history=None` + `if history is None: history = []` (Wed 5/7 same pass).
> - Pre-baseline check (now optional under new plan): confirm `OPEN_AI_MODEL = "gpt-4.1-nano"` (not "gpt-5.5") in `answer.py`.
> - Naming flag (non-blocking): current `mrr` is keyword-MRR not query-MRR. Either rename to `keyword_mrr` or add docstring before publishing numbers anyone quotes.
> - **NEW:** `get_llm_client()` factory function — Wed 5/7. Wraps `OpenAI()` vs `AzureOpenAI()` selection by env var. All LLM calls in beer_rag_app route through it.
> - **NEW:** Container App deployment design — Sat 5/10 decision: vector_db baking strategy, env var management for OPENAI_API_KEY (later AZURE_OPENAI_ENDPOINT/KEY/API_VERSION), how to expose middleware endpoint URL to agent.

> **Old session restart pointer (2026-05-02) preserved below for the day-by-day Days 1-3 sprint sections — still useful as Track B history but the rewriter+reranker comparison-table objective is now dropped per 2026-05-04 pivot. Sat 5/2 / Sun 5/3 plan was the prior week; the actual outcomes are in Daily Metrics 5/1 fenced block + Weekly Plan 4/28 archive.**
>
> **PIVOT 2026-05-01 — Two parallel tracks now, not a single sprint:**
> - **Track P (pricer skill build)** — Ed Donner LLM Engineering Wk 6 day1-5 spread over 2 weeks. Fine-tuning mechanics on a non-BBC dataset. Skill acquisition for the eventual BBC fine-tune step.
> - **Track B (Beer Intel app — ongoing)** — beer_rag_app continues. Real business value. Demo-able artifact target ~5/16. Gets quality improvements (rewriter, reranker, chunking iteration) THIS weekend.
> - **Multi-month arc (per BBC IIP north star):** Each Ed Donner concept applies to Beer Intel as homework next window. Wk 6 fine-tune → BBC tuned embeddings + generative ("speak beer") fine-tune. Wk 7 agents → agentic RAG / tool routing. Wk 8 capstone → integration. Project grows as engineer skills up; no demo deadline pressure.
> - **AI Stacks L-credentials deprioritized** per 2026-05-01 user feedback. Real capability framing only. Azure + Databricks reintroduced when pricer stable as "deploy a service" / "join Databricks data" applied work, not L-gap closures.
>
> **Where we are (end of Thu 2026-04-30 work session):** Beer Intel sprint Days 1-2 fully shipped. Day 3 partially. State on disk:
> - `beer_rag_app/ingest.py` — full pipeline working: 1457 docs → 7128 chunks → 6964 vectors in Chroma collection `beer_rag` at `sandbox/beer_rag_app/vector_db/`.
> - `beer_rag_app/answer.py` — query flow: `fetch_content` → `make_rag_messages` → `answer_question`. v0.1 smoke-tested.
> - `beer_rag_app/app.py` — Gradio chat wired through `answer_question`. Title "Beer-O-Matic".
> - `beer_rag_app/evals/evaluation.py` — `TestQuestion` Pydantic + `load_tests` + retrieval metrics (`keyword_coverage`, `mrr`, `ndcg`) + `run_baseline()` aggregator + real `evaluate_retrieval` calling `fetch_content` (replaced fake smoke from 4/29).
> - `beer_rag_app/test.jsonl` — 100 curated test queries.
> - **Day 2 baseline run NOT yet executed.** Code shipped Thu, run pending Sat. OBSERVATIONS.md baseline section unwritten.
> - **Day 3 pro techniques (rewriter, reranker, LLM chunking) — NOT YET BUILT.** Saturday sprint adds rewriter + reranker, per 2026-05-01 plan.
>
> **Immediate handoff state for Saturday 2026-05-02:** Beer Intel sprint day. Three blocks back-to-back: (1) run vanilla baseline → "Vanilla" row in OBSERVATIONS.md, (2) implement query rewriter (HyDE or multi-query) → re-run → "+ Rewrite" row, (3) implement reranker (Cohere Rerank API or BAAI/bge-reranker-base local) → re-run → "+ Rerank" + "+ Both" rows. Output: 4-row comparison table + 1 paragraph in OBSERVATIONS.md identifying which combo wins and where it fails. Tuesday's architecture decision (vanilla vs graph-RAG vs agentic) uses these results.
>
> **Sunday 2026-05-03 = pricer + reading day.** Ed Donner Wk 6 Day 1 (`~/llm_engineering/week6/day1.ipynb`) + Chip Huyen Ch 7 Finetuning + close Ch 6.
>
> **Operational TODOs flagged but deferred:**
> - Re-running `ingest.py` currently re-embeds the whole corpus (~$0.02 each run). Add `--reingest` flag gating later if iteration cost becomes annoying.
> - `crete_embeddings` typo (function name) — fix when next touching ingest.py.
> - Mutable default arg `history=[]` in `answer.py` — fix to `history=None` + `if history is None: history = []`.
> - Pre-baseline check Sat morning: confirm `OPEN_AI_MODEL = "gpt-4.1-nano"` (not "gpt-5.5") in `answer.py` before first eval run.
> - Naming flag (non-blocking): current `mrr` is keyword-MRR not query-MRR. Either rename to `keyword_mrr` or add docstring before publishing numbers anyone quotes.

**Window:** ~~Fri 2026-04-24 → Sun 2026-04-26~~ → **Slipped: Mon 2026-04-27 → Wed 2026-04-29** (3 days, ~2–3 hrs/day). Weekend lost to unplanned family commitments. Friday's chunker work stays banked; Days 1-3 below shift to Mon/Tue/Wed.
**Roadmap tie-in:** [[BBC Industry Intel Platform]] Week 2 — knock-on effect: Week 3 (FastAPI + Docker) shifts from 4/28–5/4 to **4/30–5/4** (compressed from 7 to 5 days). Acceptable because DataQuest Part 4 (FastAPI/Docker conceptual track) can absorb some compression.

**Working agreement update (2026-04-27):** The user writes the AI-engineering code — embeddings batching, Chroma collection design, retrieval pipeline, prompt engineering, eval harness, eval metric math. This is the L3 work the sprint exists to do. The assistant writes only **fiddly string/regex/glue code that the user explicitly delegates** (today's example: YAML-frontmatter stripping, where the user already has working code in another notebook to paste in). Default for everything else: the user writes it; the assistant directs, reviews, and explains Python idioms when they're unfamiliar.
**Inspiration:** Ed Donner LLM Engineering week 5, days 3–5 (`~/llm_engineering/week5/day3.ipynb`, `day4.ipynb`, `day5.ipynb`).

---

## 1. Goal (revised 2026-05-01)

**Two tracks running in parallel toward the BBC Industry Intel Platform north star** (per [[BBC Industry Intel Platform]] North Star Architecture section):

### Track B — Beer Intel app (ongoing, real business value)

Take `beer_rag_app/` from "RAG breathes + retrieval metrics" to a **demo-able, deployable agentic intelligence service**. Layered improvements over multiple windows:

1. ✅ **Pipeline + retrieval metrics** (Days 1-2 — done 4/27-4/30, baseline run pending)
2. **Sat 5/2:** query rewriter + reranker. 4-row comparison table in OBSERVATIONS.md. (THIS WEEKEND)
3. **Wed 5/7:** chunking iteration based on rewriter+reranker findings.
4. **Tue 5/6:** architecture decision (vanilla vs graph-RAG vs agentic) informed by Sat results.
5. **Wk 5/12-5/16:** apply pricer pattern → BBC-tuned embeddings ("speak beer" interpretation #1).
6. **Wk 5/19-5/23+:** generative LM fine-tune ("speak beer" interpretation #2).
7. **Wk 5/26+:** agentic RAG layer (tool routing — wiki retrieval / Databricks query / fine-tuned model).
8. **Q2 (deferred from earlier roadmap):** Azure deployment + Salesforce callout (NGEN-5882/5883 plumbing already proven 5/1; deployment effort ~4-5 days when prioritized).
9. **Q3:** persona routing (brand-mgr vs sales-rep) + held-out eval harness.
10. **Q4:** base-vs-tuned model evaluation + stakeholder writeup.

### Track P — Pricer skill build (Ed Donner Wk 6 days 1-5)

Capstone fine-tuning project on a non-BBC dataset. **Skill acquisition for the eventual BBC fine-tune step.** Days 1-5 spread Sat 5/3 → Fri 5/9 (one per day, ~2h each). Wk 6 closes Fri 5/9 ✅. Then Wk 7 (agents) + Wk 8 (capstone) extend through ~5/23.

**No sprint deadline. No demo gate.** Project grows as engineer skills up. Show something cool every ~2 weeks; multi-month arc compounds.

### Where the code lives
- `~/ai-engineering/sandbox/beer_rag_app/` — Track B
- `~/llm_engineering/week6/` — Track P (Ed Donner pricer)
- `~/llm_engineering/week7/`, `week8/` — Track P (agents + capstone, future windows)

---

## 2. Why this matters (DEPRECATED 2026-05-01 — L-credential framing dropped)

> **Section deprecated per 2026-05-01 user feedback.** AI Stacks L-level credentials (L1→L2 advancement on Microsoft / OpenAI / Anthropic / Google / Ollama) are no longer used as motivators. Real-capability framing replaces this — "deploy a service to Azure," "join Databricks data into RAG," "fine-tune a model that speaks beer." Original L-level table preserved below as historical context only. The L-table in `~/Documents/Obsidian Vault/Notes/BBC Industry Intel Platform.md` Peter Strategy Self-Assessment section remains for Peter check-ins.

**Capability scoreboard (artifacts > credentials) — current framing:**
- ✅ beer_rag_app pipeline + retrieval metrics shipped
- ⚪ 4-row comparison (vanilla / +rewrite / +rerank / +both) — Sat 5/2
- ⚪ First fine-tuned model on disk (pricer) — by Fri 5/9
- ⚪ Architecture decision (vanilla / graph-RAG / agentic) — Tue 5/6
- ⚪ BBC-tuned embeddings ("speak beer" #1) — by Fri 5/16
- ⚪ Generative LM fine-tune ("speak beer" #2) — Wk 5/19-5/23
- ⚪ Agentic RAG layer (tool routing) — Wk 5/26+
- ⚪ Azure deploy + SF callout — Q2-Q3 (NGEN-5882/5883 plumbing already proven 5/1)
- ⚪ Databricks data join — Q3 (after Azure deploy)

<details>
<summary>Historical L-level table (deprecated)</summary>

| Area | Now | Target | What this sprint contributes |
|---|---|---|---|
| **RAG Pipelines** | L2 | L3 | End-to-end retrieval + rerank + query-rewrite + eval harness on BBC data is direct L3 evidence. |
| **Using Primitives** | L2→L3 | L3 | Chunk boundaries, embedding choice, similarity math, top-K retrieval — all hand-written, no black-box. |
| **Prompt Engineering** | L2 | L3 | System prompts for QA, rerank ordering, and query rewriting are three distinct structured-output prompts. |
| **Production Concerns** | L1 | L2 | Module boundaries + eval harness; full closure needs FastAPI+Docker step (deferred). |
| **AI Stacks — OpenAI** | L1 | L2 | OpenAI embeddings API + structured outputs + LLM-as-judge all exercised. |

</details>

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
- [x] Write `app.py` (done 2026-04-29):
  - `chat(message, history)` adapter unpacks the `(str, list)` tuple → returns `str`. `gr.ChatInterface(chat, title="Beer-O-Matic").launch(inbrowser=True)`. Gradio 6.10 dropped the `type` kwarg (messages format is now default).
- [ ] Run it. Ask ~10 BBC-relevant questions. **DEFERRED** — eval harness numbers will replace eyeball judgments; revisit only if eval surfaces unexplained behavior.
- [x] Cleanup before commit: remove debug `print` on `answer.py` line 35.

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
- [x] Create `evals/` package with `__init__.py` (named `evals/`, not `evaluation/` per plan — matches existing scaffold; `beer_rag_app/__init__.py` also added so `python -m` works).
- [x] Write `evals/evaluation.py` — combined Pydantic + metrics file (plan called for split `test.py` + `eval.py`; user chose single file):
  - `TestQuestion` Pydantic model: `question, keywords, reference_answer, category`.
  - `load_tests() -> list[TestQuestion]` reading `tests.jsonl` (named `test.jsonl` at package root).
- [x] `tests.jsonl` — 100 queries from `sandbox/test.jsonl` moved to `beer_rag_app/test.jsonl`. Categories: `direct_fact`, `entity`, `comparative`, `temporal`, `spanning`, `regulatory`. Plan asked 20–30; kept all 100 (data-rich = no curation work; runtime cost manageable for retrieval-only eval). Filter later if LLM-judge runtime hurts.
- [x] Retrieval metric helpers written and smoke-tested on golden case (1.0/1.0/1.0):
  - `keyword_coverage(keywords, retrieved_docs)` — fraction of keywords found anywhere in top-K (case-insensitive).
  - `reciprocal_rank(keyword, retrieved_docs)` — `1/rank` of first match. `mrr(keywords, retrieved_docs)` aggregates avg.
  - `calculate_dcg`, `calculate_ndcg(keyword, retrieved_docs, k=10)` (binary relevance, copied from Ed Donner). `ndcg(keywords, retrieved_docs, k=10)` aggregates avg.
  - Stress test confirmed metric divergence: 2-doc list with keyword in doc 2 → coverage=1.0, mrr=0.5.
- [ ] Write `evaluate_retrieval(test) -> dict` — orchestrator: one `fetch_content` call, run all three metrics on the result. (Day 2 finish.)
- [ ] Run baseline: loop over all 100 tests, aggregate per-category, save to `OBSERVATIONS.md` under "Day 2 baseline".
- [ ] **Slipped to Thursday 2026-04-30:** `evaluate_answer(test)` (LLM-as-judge: accuracy/completeness/relevance) + `evaluate_all_*` generator variants + `dashboard.py` Gradio port from `~/llm_engineering/week5/evaluator.py`.

**Pre-baseline blocker:** `answer.py:11` currently set to `OPEN_AI_MODEL = "gpt-5.5"` (not a real model). Revert to `"gpt-4.1-nano"` before running `evaluate_retrieval` — first call will 400 otherwise.

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

## 6. After this 2-week window — where this hands off

This window (5/2 → 5/9) closes:
- **Beer Intel:** baseline numbers + rewriter + reranker + 4-row comparison + architecture decision + chunking iteration + dataset schema for embedding fine-tune.
- **Pricer:** Wk 6 days 1-4 done; day 5 done OR carrying.
- **Reading:** Chip Huyen Ch 6, 7 ✅; Ch 8 ✅ or 🟢.

### Next window (5/12 → 5/16) — apply pricer to BBC

- **Track B:** First BBC-tuned embeddings. Apply pricer day-2 dataset patterns + Ch 8 dataset engineering principles. Pull wiki corpus, format as training pairs, run embedding fine-tune. Swap into `beer_rag_app/answer.py` `fetch_content`. Re-run baseline → measure tuned-vs-base retrieval delta. Cool demo target ~5/16: "BBC-tuned embeddings retrieval comparison."
- **Track P:** Pricer Wk 6 day 5 close (if not Fri 5/9). Begin Wk 7 (agents) reading.

### Following windows (5/19+) — multi-month arc

| Window | Track B (Beer Intel) | Track P (skill) |
|---|---|---|
| 5/19-5/23 | Generative LM fine-tune ("speaks beer" #2) | Ed Donner Wk 7 agents |
| 5/26-5/30 | Agentic RAG layer + tool routing | Ed Donner Wk 8 capstone |
| Jun-Jul | Azure hosting + Salesforce callout (NGEN plumbing exists) | Next agents course |
| Q3 | Persona routing + Databricks data join | — |
| Q4 | Base-vs-tuned eval + stakeholder writeup | — |

### What explicitly does NOT go in this 2-week window (scope discipline)

- No FastAPI / Docker / Azure deploy. (Defer to later windows when pricer track stable. Q2 RAG-on-Azure milestone explicitly slipped per 5/1 pivot.)
- No LLM-driven chunking. (Would require re-ingest into separate `beer_rag_pro` Chroma collection — too large for current windows.)
- No LLM-judge `evaluate_answer` (Day 2 stretch). (Defer.)
- No Databricks data join (Q3 milestone — needs Azure deploy first).
- No Salesforce callout integration (Q3+ — the plumbing exists from NGEN-5882/5883 but the agent must be deployed first).

If any of those feel tempting mid-window, write them into `OBSERVATIONS.md` under "Deferred ideas" and move on. The discipline is: each window adds one capability layer, doesn't try to skip ahead.

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

### Wed 2026-04-29 — Day 1 closed; Day 2 retrieval metrics written; baseline + LLM-judge + dashboard slip to Thursday
- Start time: ~late afternoon
- End time: ~evening (faded out — user flagged fatigue mid-session)
- Blocks completed:
  - `app.py` — Gradio chat wired through `answer_question`. Fixed two bugs live: returned tuple instead of unpacked str (Gradio rendered weird); passed `type="messages"` (Gradio 6.10 dropped that kwarg, messages format is now default).
  - `evals/` package + `beer_rag_app/__init__.py` to make `python -m` launches work.
  - `evals/evaluation.py` (combined Pydantic + metrics file): `TestQuestion`, `load_tests`, `keyword_coverage`, `reciprocal_rank`, `mrr`, `calculate_dcg`, `calculate_ndcg`, `ndcg` aggregator. All three metrics smoke-tested 1.0/1.0/1.0 on golden-case (keyword-bearing reference answer as the only chunk). Stress test confirmed coverage vs. mrr divergence with a 2-doc decoy case (1.0 vs 0.5).
  - `tests.jsonl` (100 queries) moved into `beer_rag_app/`. Loader resolves it via `__file__.parent.parent`.
  - Cleanup: removed debug `print` on `answer.py:35`.
- Blocks NOT completed (slipping to Thursday 2026-04-30):
  - `evaluate_retrieval(test) -> dict` orchestrator (the actual loop that calls `fetch_content` + runs all three metrics).
  - **Run the baseline**: 100 tests through retrieval eval, per-category aggregation, `OBSERVATIONS.md` "Day 2 baseline" table.
  - LLM-judge `evaluate_answer` + `evaluate_all_*` generators.
  - `dashboard.py` Gradio port.
  - 10 BBC vibe-check questions + `OBSERVATIONS.md` Day 1 impressions section (deferred — eval will replace eyeballing if it produces clean signal).
- Pre-baseline blocker: `answer.py:11` set to `OPEN_AI_MODEL = "gpt-5.5"` (non-existent). Revert to `"gpt-4.1-nano"` before Thursday's first eval run.
- What worked:
  - **Architectural redirect on metric signature** — user's first draft of `keyword_coverage(keywords, top_k=5)` couldn't work (no chunks to scan). Surfaced the retrieve-once / score-many architecture explicitly. Each metric is now stateless and unit-testable against hand-built `Result` lists with no Chroma.
  - **Iterative bug-fix cadence** — keyword_coverage v1 had four bugs (inverted formula, double-count, case-sensitive, wrong type). Walked through all four in one review, user fixed in one pass, smoke test confirmed correctness next iteration. MRR landed clean on first try.
  - **Stress test caught the conceptual point** — 2-doc decoy showed coverage stays 1.0 while MRR halves. Made the metric semantics tangible: coverage = reach, mrr = ranking.
  - **Library-version archaeology** — `inspect.signature(gr.ChatInterface.__init__)` to confirm Gradio 6 dropped `type` kwarg in 30 seconds. Faster than docs, never wrong about the installed version.
- What got stuck:
  - **Wall-of-text feedback** — early in session, multi-decision menus + parallel insight blocks made it hard to track the next step. User flagged it; saved to memory (`feedback_response_length.md`) — keep one decision per turn going forward.
  - **Method-vs-call typo** — `doc.page_content.lower` (missing parens) inside a generator — easy to miss because no syntax error, fails only at iteration with a confusing `TypeError: argument of type 'method' is not iterable`. Worth banking as a Python idiom watch.
  - **Smoke-test arg shape** — user passed full `keywords` list to per-keyword `calculate_ndcg`; needed the aggregator first. Reinforced: per-keyword helpers + per-test aggregators are different layers.
- Concepts driven home today:
  - **Retrieval-once + stateless metrics** — design pattern for any eval harness, not just RAG. Metrics that pull their own data are 3× more expensive and not unit-testable.
  - **Coverage vs MRR as orthogonal signals** — one tells you the retriever can reach relevant material; the other tells you it ranks relevant material near the top. Both can be high; both can be low; they diverge when ranking is bad relative to recall. Different fixes.
  - **nDCG IDCG with binary relevance** = "what's the best rearrangement of what was actually found" — sorting the actual relevances descending = all 1's at top. Returns 0.0 if nothing found (the guard).
- Commit SHA: (pending)

### Day 3 — pro mode + ablations — **PARTIALLY RESCOPED — rewriter + reranker land Saturday 2026-05-02**
Originally scheduled for Wed 2026-04-29; first rescoped to Week 3 carryover; now Saturday 5/2 absorbs the rewriter + reranker portion as a concentrated Beer Intel sprint day (per 2026-05-01 pivot — pricer track Track P parallel-builds, Beer Intel Track B continues with quality improvements). LLM-driven chunking still deferred (would require re-ingest into a separate `beer_rag_pro` collection — not Saturday-sized work). Ablations land Wednesday 5/7 evening as chunking iteration informed by Saturday's 4-row comparison.

### Thu 2026-04-30 — Day 2 baseline aggregator + real smoke shipped
- Start time: ~late afternoon
- End time: ~evening
- Blocks completed:
  - Replaced fake `__main__` smoke in `evals/evaluation.py` with real `fetch_content(test.question)` call. Smoke now validates the full retrieval path, not a tautology.
  - Reverted `OPEN_AI_MODEL` to `"gpt-4.1-nano"` (was "gpt-5.5", non-existent).
  - Wrote `evaluate_retrieval(test, k=10)` orchestrator + `run_baseline()` per-category aggregator per the assistant-suggested shape from Wed review notes.
  - `app.py` Gradio module verified launching against persisted Chroma.
- Blocks NOT completed (slipping to Sat 5/2):
  - **The actual run.** `run_baseline()` exists; never executed against full 100 tests. No numbers in `OBSERVATIONS.md` yet.
  - LLM-judge `evaluate_answer` + `dashboard.py` Gradio port — still pending (Day 2 stretch).
- What worked:
  - Wed review notes were directly actionable; Thursday work was largely "execute the plan" rather than re-deciding.
  - Stateless metric design from Wed paid off — building the orchestrator was a thin loop, not a redesign.
- What got stuck:
  - Time pressure ate the actual run. Code was ready; running 100 tests + writing observations needed another 30-45 min that evening didn't have.
- Commit SHA: `c59cd87` (last carryover commit visible in 2-week git log).

### Fri 2026-05-01 — No work session; cyber alerts ate the day
- Start time: N/A
- End time: N/A
- Blocks completed: zero. Day eaten by cybersecurity false-alarm alert triage. All 3 meetings (weekly connect, Customer Sets, April Roundup) held. Wiki system updates shipped on the side (knowledge codification — counts as Goal 3, not formal sprint progress).
- **Sprint pair status correction:** NGEN-5882/5883 round-trip POC end-to-end proven — Salesforce → Databricks (via Azure Function) → Salesforce. Connected App built. Flight logs at `~/.claude/flight-logs/NGEN-588[2,3].md` were stale at session start; pricer/RAG architectural reasoning now factors this as DONE.
- **Plan revision happened in evening session 5/1:** Two-track parallel structure formalized. Pricer prioritized for skill acquisition; Beer Intel ongoing for business value. Multi-month arc (Wk 6 → Wk 7 → Wk 8 → next agents course) → mapped onto BBC IIP north star (deploy + Databricks join + agentic loop). User explicitly: "I am not worried if DW numbers seem shallow. I consider study a form of deep work" given AI Capability Center role. AI Stacks L-credential framing deprioritized; real-capability framing only.
- Commit SHA: N/A

### Sat 2026-05-02 — BEER INTEL SPRINT DAY (planned ~4h)
**Track B sprint day. Pricer paused; Sunday picks up.**
- Block 1 (60 min): Vanilla baseline run. `python -m beer_rag_app.evals.evaluation` `run_baseline()` against persisted Chroma + 100-test set. Capture per-category MRR / nDCG / keyword_coverage as "Vanilla" row in `OBSERVATIONS.md`. **Pre-flight:** confirm `OPEN_AI_MODEL = "gpt-4.1-nano"` in answer.py before running.
- [10-min break]
- Block 2 (75 min): Add query rewriter to `answer.py`. Pick (a) HyDE — single LLM call generates hypothetical answer, embed THAT instead of question; OR (b) multi-query — LLM expands into 2-3 variants, retrieve all, dedupe. Recommend HyDE first (simpler). Re-run `run_baseline()` → "+ Rewrite" row.
- [10-min break]
- Block 3 (90 min): Add reranker to `answer.py`. Pick (a) Cohere Rerank API — `pip install cohere`, ~$1/1000 queries, ~5 lines code; OR (b) `BAAI/bge-reranker-base` — HuggingFace cross-encoder, free, slower, requires sentence-transformers. Recommend Cohere first for sprint speed; can swap later. Take top-20 from vector search → rerank → top-5 to LLM. Re-run baselines → "+ Rerank" + "+ Rewrite + Rerank" rows.
- **Deliverable:** `OBSERVATIONS.md` 4-row comparison table (Vanilla / +Rewrite / +Rerank / +Both) per category + 1 paragraph identifying winning combo and where it fails. The "where it fails" paragraph is the input to Tuesday's architecture decision (vanilla vs graph-RAG vs agentic).
- **Skip if running long:** the LLM-judge / dashboard / chunking iteration. Those land later in window.

### Sun 2026-05-03 — PRICER + READING DAY (planned ~4h)
**Track P opens. Track B in reading mode.**
- Block 1 (135 min) [P]: Ed Donner Wk 6 Day 1 — `~/llm_engineering/week6/day1.ipynb` end-to-end. BUILD mode: run every cell, modify one thing, understand what pricer is solving (regression vs classification for price prediction? Synthetic data shape?). Deliverable: 3-line vault note on pricer mechanics.
- [15-min break]
- Block 2 (90 min) [P/B]: Chip Huyen Ch 7 Finetuning. Read; pairs both pricer mechanics AND BBC embedding/generative tune planning. Deliverable: 2-sentence note on PEFT vs full fine-tune.
- [15-min break]
- Block 3 (30 min) [B]: Chip Huyen Ch 6 RAG and Agents — close out chapter. Vocabulary for Tuesday's architecture decision.

### Mon 2026-05-05 — PRICER DAY 2 (home, ~2h) [P]
Ed Donner Wk 6 Day 2 — synthetic data + dataset shaping cells. Cascaded from Sun (Beer Intel sprint took Saturday, push pricer day2 to Monday). Note overlap with existing `~/ai-engineering/sandbox/synthetic_data_generator.ipynb` for BBC fine-tune dataset prep later.

### Tue 2026-05-06 — ARCH RESEARCH + PRICER DAY 3 (Boston, ~2h)
- Train (60 min) [B]: Beer Intel architecture research. Read 1 source on graph-RAG (Microsoft GraphRAG paper or blog) OR agentic RAG (LlamaIndex blog) — informed by Saturday's "+ Rewrite + Rerank" failure cases. If multi-hop queries broke, lean graph-RAG. If query routing seems missing, lean agentic. 1-page vault note on architecture choice + rationale.
- Eve (60 min) [P]: Ed Donner Wk 6 Day 3 — pricer fine-tune trial. First fine-tuned model artifact on disk.

### Wed 2026-05-07 — CHIP HUYEN CH 8 + BEER INTEL CHUNKING (Boston, ~2h)
- Train (60 min) [R]: Chip Huyen Ch 8 Dataset Engineering — direct prep for BBC embedding fine-tune dataset.
- Eve (60 min) [B]: Beer Intel chunking iteration. Use Saturday findings: if reranker masked weak retrieval, try smaller chunks. If rewriter helped multi-word queries, try metadata filtering on entity hits. Code change committed; re-run baseline subset.

### Thu 2026-05-08 — DATASET SCHEMA + PRICER DAY 4 (Boston, ~2h)
- Train (60 min) [R]: Chip Huyen Ch 8 finish + sketch BBC fine-tune dataset format (jsonl shape derived from pricer day2 patterns). Dataset schema decision documented.
- Eve (60 min) [P]: Ed Donner Wk 6 Day 4 — pricer eval/inference. Base vs fine-tuned comparison numbers on pricer test set.

### Fri 2026-05-09 — PRICER WK6 CLOSE OR BBC EMBED SCAFFOLD (home, ~2h) [P/B]
Pricer Day 5 wrap (`results.ipynb` if that's where day5 lives) → Wk 6 ✅. If day5 stalls or already done, start BBC embedding fine-tune scaffold: pull wiki corpus, format as training pairs, apply Ch 8 + pricer day2 patterns. Output: pricer Wk 6 closed OR `beer_embed_finetune.py` scaffolded.

---

## Thursday 2026-04-30 — Eval Harness Review Notes (assistant-authored 2026-04-29 EOD)

End-of-Wednesday review of `sandbox/beer_rag_app/evals/evaluation.py` + `answer.py` + `app.py`. Pickup work for Thursday's Day 2 close.

### Critical bug — fix first

**The `__main__` smoke test in `evals/evaluation.py` is fake.** It builds `docs = [Result(page_content=test.reference_answer, metadata={})]` — putting the reference answer INTO a doc, then asking "do keywords appear in this doc?" Of course they do. Coverage will always return 1.0 on this smoke. **The retriever is never called.** The smoke proves nothing about the actual pipeline.

Fix:
```python
from beer_rag_app.answer import fetch_content  # adjust to match import style chosen below
docs = fetch_content(test.question)  # real retrieval against persisted Chroma
```

Without this, today's metric correctness verification is a tautology. Spend 15 min Thursday morning replacing the fake smoke with a real one before doing anything else on the eval harness.

### Pre-baseline blocker (already flagged in Wed log)

`answer.py:11` is set to `OPEN_AI_MODEL = "gpt-5.5"` (not a real model). Revert to `"gpt-4.1-nano"` before the first `evaluate_retrieval` run — first call will 400 otherwise.

### Naming / shape concerns (worth flagging in code comments, not blocking)

1. **`mrr` is keyword-MRR, not query-MRR.** Standard MRR averages reciprocal rank across **queries** (one rank per query). Current `mrr` averages across **keywords** within one query. It's a reasonable custom metric but doesn't match literature MRR. Either rename to `keyword_mrr` / `avg_first_keyword_rank`, or leave the name and add a 2-line docstring stating "this aggregates per-keyword reciprocal ranks within a single query, not per-query MRR across the test set."

2. **`ndcg` aggregates per-keyword nDCG then averages.** Same shape concern — standard nDCG uses a single relevance vector per query. Two cleaner alternatives:
   - Binary OR: `relevance[i] = 1 if any(kw in chunk[i]) else 0`, then standard nDCG.
   - Graded: `relevance[i] = count of matching keywords`, then standard nDCG.
   Either gives query-level nDCG matching literature. Current per-keyword averaging is acceptable for v0.1 but flag it before publishing numbers anyone will quote.

### Code-hygiene fixes (cheap wins)

3. **Import path mismatch.** `evaluation.py` uses `from sandbox.beer_rag_app.ingest import Result` (absolute from repo root). `answer.py` uses `from ingest import Result` (relative-style). Will break depending on cwd. Pick one shape and apply consistently. Recommend: `from beer_rag_app.ingest import Result` everywhere, run from `sandbox/` with `python -m beer_rag_app.evals.evaluation`.

4. **Mutable default arg in `answer.py`:** `def answer_question(question, history=[])`. Classic Python footgun — list shared across all calls without an explicit override. Fix:
   ```python
   def answer_question(question, history=None):
       if history is None:
           history = []
   ```

5. **Unused imports in `answer.py`:** `tenacity` (`retry`, `wait_exponential`), `litellm.completion`, `BaseModel`, `Field`, `Path`. Strip or wire them up. Either option is fine; just don't leave dead imports.

6. **Smoke test seeds `metadata={}` but `make_rag_messages` requires `metadata['source']`.** Different code paths so not currently breaking, but inconsistent. Once smoke uses real `fetch_content`, this resolves naturally.

### Missing piece — aggregating runner

The metric helpers exist; the harness top doesn't. Plan-of-record `evaluate_retrieval(test) -> dict` was the next task. Suggested shape:

```python
def evaluate_retrieval(test: TestQuestion, k: int = 10) -> dict:
    docs = fetch_content(test.question)
    return {
        "question": test.question,
        "category": test.category,
        "coverage": keyword_coverage(test.keywords, docs),
        "mrr": mrr(test.keywords, docs),
        "ndcg": ndcg(test.keywords, docs, k=k),
    }


def run_baseline():
    tests = load_tests()
    rows = [evaluate_retrieval(t) for t in tests]
    # aggregate per-category
    from collections import defaultdict
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    for cat, group in by_cat.items():
        avg_cov = sum(r["coverage"] for r in group) / len(group)
        avg_mrr = sum(r["mrr"] for r in group) / len(group)
        avg_ndcg = sum(r["ndcg"] for r in group) / len(group)
        print(f"{cat:15} n={len(group):3} cov={avg_cov:.3f} mrr={avg_mrr:.3f} ndcg={avg_ndcg:.3f}")
    return rows
```

That's the deliverable that closes Day 2 retrieval baseline. Save the printed table into `OBSERVATIONS.md` under "Day 2 baseline" with date stamp.

### Strong design choices to preserve

- **Categorizing test questions** (`direct_fact`, `entity`, `comparative`, `temporal`, `spanning`, `regulatory`) is gold for Q3 persona-routing. Per-category metric breakdowns will surface where retrieval breaks (spanning likely worse than direct_fact). Don't lose this dimension.
- **Stateless metric helpers** (run on caller-provided `list[Result]`) is the right factoring. Keeps unit-testable; keeps the loop that calls retrieval separate from the loop that scores. Preserve this even when adding LLM-judge — `evaluate_answer(test, retrieved_docs, generated_answer)` should also be stateless.
- **Pydantic `TestQuestion` + JSONL on disk** is the right test schema shape. Fast to load, easy to git-diff, easy to extend (just add a field, old rows still parse if field is `Optional`).

### Suggested Thursday block sequence (~2-3 hr)

1. **Pre-baseline triage (15 min):** revert `OPEN_AI_MODEL` to `"gpt-4.1-nano"`. Fix import path mismatch (pick package-relative everywhere). Fix mutable default `history=[]`. Strip unused imports.
2. **Real smoke test (15 min):** rewrite `evals/evaluation.py` `__main__` to call `fetch_content(test.question)` instead of fabricating a doc from `reference_answer`. Verify metrics produce sensible non-tautological numbers on test 0.
3. **Aggregating runner (45-60 min):** write `evaluate_retrieval(test)` + `run_baseline()` per the shape above. Run it. Capture the per-category table.
4. **Write `OBSERVATIONS.md` Day 2 baseline section (30 min):** one paragraph on which category performs worst + a hypothesis why. Three-decimal precision on the metrics. Note the worst-performing category as the candidate for Day 3 pro-technique testing.
5. **Stretch — `evaluate_answer` LLM-judge skeleton (30-45 min):** if time remains. Pydantic `JudgeScore { accuracy, completeness, relevance }` + judge prompt + `evaluate_answer(test, retrieved_docs, generated_answer) -> JudgeScore`. Don't run on all 100 tests yet — wire it through one test as a smoke; full LLM-judge baseline is a bigger budget conversation.

### Open question for Thursday's Brooks

Plan §6 calls for FastAPI to wrap "a working evaluated module." Day 2 baseline is the *evaluated* part. Once retrieval baseline is in `OBSERVATIONS.md`, the FastAPI wrapper can start in parallel with Day 3 pro-techniques rather than after — they touch different files. Worth considering when planning Friday/weekend allocation.

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
