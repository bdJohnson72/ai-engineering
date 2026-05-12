# SOTO Agent — Project Context

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

## Where we left off (end of 2026-05-12)

**Steps 1-5 done + Dockerfile pushed to ACR. Container App not yet created.** Next session opens with `az containerapp create` against the just-pushed image.

Today's progress (Tue 5/12):
- `tools/glossary_lookup.py` — boot-load parser (55 canonical + 7 ambiguities); merge-on-overlap (e.g. "Promotion") surfaces both definition + ambiguity note. Wired into `app.py` TOOLS/_DISPATCH; `_serialize_tool_result` generalized to any pydantic BaseModel.
- `tests/test_glossary_lookup.py` — first pytest file in the repo, 19 cases, all green.
- `server.py` — FastAPI `POST /soto-agent`; sync route, Pydantic request body, error path uses `logger.exception` + 500 HTTPException.
- `scripts/build_vault_subset.py` — denylist filter of local Obsidian vault into `soto_agent/data/vault/`. Filters `index.md` rows in place (preserves curated 1-liners).
- `Makefile` — test / refresh-glossary / vault / prep / image / deploy / run / clean.
- `data/ubiquitous-language.md` — committed copy of the glossary. Source-of-truth still in BCC_NGST_CG; `make refresh-glossary` syncs.
- `data/vault/` — gitignored build artifact (1600 files / 6.1 MiB).
- `Dockerfile` + slim `requirements.txt` + `.dockerignore` — python:3.12-slim, ~150-200 MB image.
- **First image pushed:** `bbcsotoacr.azurecr.io/soto-agent:latest` via `az acr build` (37s).
- Wiki bug fixed mid-session — page-selector LLM had been inventing a `Entities/` folder prefix from the stats-table category label. Hardened the selector prompt + added a basename-rglob fallback in `_resolve_page_path`.

Smoke tests via `make run` + curl confirm:
- Glossary lookup roundtrip (merge case for "Promotion").
- Wiki search → read → synthesize on "Who is Matt Withington?" using the **subset** vault (`VAULT_PATH=soto_agent/data/vault`).

Carries to Wed 5/13:
- `server.py` needs a `/health` endpoint before Container App probes can succeed.
- `az containerapp create` not yet run. No FQDN yet.
- Env-var matrix for the container is unwritten (next session's first artifact).

## Where we left off (end of 2026-05-08)

**Steps 1-3 done. Three models benchmarked. ACR provisioned. Ready for Mon 5/11 deploy work.**

What runs end-to-end today:

```bash
cd ~/ai-engineering
uv run python -m soto_agent.app --model gpt-4.1 "What is BBC's on-premise strategy for Sun Cruiser?"
uv run python -m soto_agent.evals.run_evals --model gpt-4.1
```

Models registered (in `soto_agent/app.py` `_MODEL_BUILDERS`):
- `gpt-4.1-mini` — default; env `AZURE_OPENAI_DEPLOYMENT_CHAT`
- `gpt-4.1` — env `AZ_GPT_FOUR_ONE`
- `gpt-5` / `gpt-5-mini` — slots only, not deployed yet
- `deepseek-v3` — env `AZ_DEEPSEEK_THREE_ONE`; same Foundry v1 surface as R1
- `deepseek-r1` — registered but **NOT usable for agent** (Azure rejects tool calls with `UnsupportedToolUse 400`); reserved for future LLM-as-judge

Multi-model eval results (4-case suite, all in `soto_agent/evals/runs/`):

| Model | Total latency | Multi-hop | Cost vs cheapest |
|---|---:|---|---:|
| `gpt-4.1` | 94s | ✓ best | 13× |
| `deepseek-v3` | 170s | ✓ ok (after MAX_TURNS bump + parallel-call prompt rule) | 1× |
| `gpt-4.1-mini` | 220s | soft fail (single-source comparison) | 1× |

For demo: lean **`gpt-4.1`**. Multi-hop reliability + speed > marginal cost savings.

Prompt fixes that have been driven by eval failures (regression tests in `evals/test_cases.jsonl`):
- Disambiguation rule (How-to-answer #2) — fired by `disamb-objective-priority-sku-001`
- Comparison-Q must read both sides (How-to-answer #6) — fired by `multihop-compare-truly-suncruiser-001`
- Tool-call efficiency (parallel batching, follow wikilinks before re-searching) — fired by V3 trace debug

### Re-ordered build plan (decision 2026-05-08)

User wants SF connected sooner. Originally tools first → FastAPI → deploy → SF. Re-ordered to **FastAPI → deploy → SF (with wiki only) → keep adding tools**. Integration spine de-risked early; tool wiring after deploys is incremental.

| When | What |
|---|---|
| **Sat-Sun 5/9-5/10** | Optional reading — Chip Huyen Ch 6 RAG/Agents (per learning posture) |
| **Mon 5/11 AM** | `glossary_lookup` (~30 min, user-driven write per recovery option C) + Step 5 FastAPI route |
| **Mon 5/11 PM** | Step 6 — first Container App deploy via `az acr build` + `az containerapp up` against `bbcsotoacr.azurecr.io` |
| **Tue 5/12** | Step 7 — SF integration. Named Credential URL swap to deployed Container App. Smoke test E2E from LWC. Live agent reachable from SF (wiki-only). |
| **Wed 5/13** | Start `databricks_query` tool wiring; smoke against warehouse |
| **Thu 5/14** | Finish `databricks_query` + start `salesforce_query` |
| **Fri 5/15** | Finish `salesforce_query`; integration testing on deployed agent |
| **Weekend 5/16-17** | Buffer / refinements (user available) |
| **Mon 5/18** | Final polish, performance check |
| **Tue 5/19** | Pre-demo dry run |
| **Wed 5/20** | CTO dry run |

## Azure resources provisioned

- **Foundry resource:** `Foundry-ITBS-POC-2` (eastus). Hosts gpt-4.1-mini, gpt-4.1, deepseek-r1, deepseek-v3.1.
- **Function App:** `sffuncpoc` (existing middleware, do-not-touch).
- **Container Registry (NEW 2026-05-08):** `bbcsotoacr` in `BBC-ITBS-POC-EastUS`. Login server `bbcsotoacr.azurecr.io`. SKU Basic (~$5/mo). Admin user disabled. User has Owner via creation. AcrPull for Container App's managed identity to be assigned at first deploy.
- **Container App:** to be provisioned Mon 5/11 (`az containerapp up`).

User has **Contributor** on `BBC-ITBS-POC-EastUS`, verified 2026-05-08.

## Wed 5/13 — runbook (sequenced, copy-pasteable)

Confirmed Tue 5/12 EOD: **no Container Apps environment exists yet** in `BBC-ITBS-POC-EastUS`. The environment is a prereq for the Container App — create it first.

```bash
SUB=cebd9dd6-bc18-4e1c-9564-bd4ec13c565b
RG=BBC-ITBS-POC-EastUS
ACA_ENV=soto-agent-env
ACA_NAME=soto-agent
ACR=bbcsotoacr
REGION=eastus
```

### Step 0 — verify state from yesterday

```bash
cd ~/ai-engineering
git log --oneline -8                                   # last commit should be the CONTEXT refresh
az account show --query name -o tsv                    # "BBC DevTest Subscription"
az acr repository show-tags --subscription $SUB -n $ACR --repository soto-agent -o table   # should show 'latest'
az containerapp env list --subscription $SUB -g $RG -o table  # confirm: no rows (env not yet created)
```

### Step 1 — add `/health` endpoint to `soto_agent/server.py`

Required for Container Apps startup/liveness probes. Smallest version:

```python
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Rebuild + push:

```bash
make -C soto_agent image
```

### Step 2 — create Container Apps environment (one-time, ~3 min)

`--logs-destination none` skips Log Analytics (cheaper for the demo; can be wired in later).

```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az containerapp env create \
  --subscription $SUB \
  --resource-group $RG \
  --name $ACA_ENV \
  --location $REGION \
  --logs-destination none
```

### Step 3 — create the Container App

The agent reads `AZURE_OPENAI_API_KEY` from env, so it must be a **secret**, not plain text. Other env vars are non-sensitive (endpoints, deployment names).

Values (from local `.env`, set fresh on Wed):
- `AZURE_OPENAI_API_KEY` — Foundry-ITBS-POC-2 key (the secret)
- `AZURE_OPENAI_ENDPOINT` — `https://foundry-itbs-poc-2.cognitiveservices.azure.com/`
- `AZURE_OPENAI_API_VERSION` — `2024-12-01-preview`
- `AZURE_OPENAI_DEPLOYMENT_CHAT` — `gpt-4.1-mini`
- `AZ_GPT_FOUR_ONE` — `gpt-4.1` deployment name (whatever you typed at deploy time)
- `SOTO_MODEL` — `gpt-4.1` (so the agent uses the larger model by default)

Other env vars from `.env` (`AZ_DEEPSEEK_*`, `AZ_EMBEDDING_*`, `AZ_TEXT_EMBEDDING_3_SMALL_KEY`) are **not needed in v1** — only used by code paths we're not running in the container.

```bash
# Read the key locally so it never lands in shell history as a literal
AOAI_KEY=$(grep '^AZURE_OPENAI_API_KEY=' .env | cut -d'=' -f2-)

az containerapp create \
  --subscription $SUB \
  --resource-group $RG \
  --name $ACA_NAME \
  --environment $ACA_ENV \
  --image $ACR.azurecr.io/soto-agent:latest \
  --registry-server $ACR.azurecr.io \
  --registry-identity system \
  --ingress external \
  --target-port 8000 \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 0.5 --memory 1.0Gi \
  --secrets azure-openai-api-key="$AOAI_KEY" \
  --env-vars \
      AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key \
      AZURE_OPENAI_ENDPOINT=https://foundry-itbs-poc-2.cognitiveservices.azure.com/ \
      AZURE_OPENAI_API_VERSION=2024-12-01-preview \
      AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4.1-mini \
      AZ_GPT_FOUR_ONE=gpt-4.1 \
      SOTO_MODEL=gpt-4.1
```

`--registry-identity system` tells Container Apps to use its own system-assigned managed identity to pull from ACR. After `create` runs, attach AcrPull:

```bash
ACA_PRINCIPAL=$(az containerapp show --subscription $SUB -g $RG -n $ACA_NAME --query identity.principalId -o tsv)
ACR_ID=$(az acr show --subscription $SUB -n $ACR --query id -o tsv)
az role assignment create --assignee $ACA_PRINCIPAL --role AcrPull --scope $ACR_ID
```

(If the ACR pull fails on first create because the role wasn't yet assigned, restart the revision with `az containerapp revision restart` or just `az containerapp update --image` after the role is in place.)

### Step 4 — smoke test against the FQDN

```bash
FQDN=$(az containerapp show --subscription $SUB -g $RG -n $ACA_NAME --query properties.configuration.ingress.fqdn -o tsv)
echo "https://$FQDN/health"
curl -s https://$FQDN/health
curl -s -X POST https://$FQDN/soto-agent \
     -H "Content-Type: application/json" \
     -d '{"question":"What is a Wholesaler Program?"}'
```

If anything looks off, tail the logs:

```bash
az containerapp logs show --subscription $SUB -g $RG -n $ACA_NAME --follow
```

### Step 5 — SF Named Credential URL swap (step 7 of the build plan)

Once the FQDN is reachable and the smoke test answers cleanly:
- Open the existing `Azure_Account_Intelligence_EC` Named Credential in the target SF org.
- Replace the URL with `https://$FQDN` (no path — Apex builds the path).
- Apex `AccountIntelligenceController` continues to call the same Named Credential; only the URL behind it moves.
- Click "Ask AI" from the `accountIntelligence` LWC. Expect wiki + glossary answers (databricks/SF tools aren't wired yet — they ship Thu-Fri).

Earlier-session runbook (Mon 5/11 — preserved for reference, not the active path):

```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az account show -o table
az acr show -n bbcsotoacr -o table
```

## Streaming UX — Path A specification (locked 2026-05-08)

Reuses existing `Account_Intelligence__e` Platform Event from PR 15651 — **no new SF metadata**. Adds a new `Status__c` value for in-flight progress events; LWC subscriber (already running in `connectedCallback`) gains a branch for it.

**PE schema (existing fields, new Status value):**

| Field | Existing values | New for Path A |
|---|---|---|
| `CorrelationId__c` | UUID per request | unchanged |
| `Status__c` | `SUCCESS`, `ERROR` | **add `PROGRESS`** |
| `Result__c` | JSON answer (on SUCCESS) | JSON `{stage, query?, page?}` (on PROGRESS) |
| `Message__c` | error text | unchanged |

**Stages emitted by agent (one PE per stage):**

| Trigger | Result__c JSON | LWC text |
|---|---|---|
| `run_agent` start | `{"stage":"started"}` | "On it — looking up your question..." |
| Each `wiki_search` call | `{"stage":"searching","query":"..."}` | "Searching wiki for *<query>*" |
| Each `wiki_read` call | `{"stage":"reading","page":"..."}` | "Reading *<page>*..." |
| Final synthesis turn (no tool_calls) | `{"stage":"drafting"}` | "Drafting answer..." |
| Final answer | `Status__c=SUCCESS` (existing path) | renders the answer |

**LWC behavior changes:**
- empApi callback already filters by `correlationId` (durable from PR 15651). Add a branch: if `Status__c === 'PROGRESS'`, parse `Result__c` and update the spinner status line; otherwise existing SUCCESS/ERROR rendering paths.
- Spinner display: single rotating line for v1 (replaces previous text). Stacked log can come post-demo if reps want a visible reasoning trail.
- Fallback: if no PROGRESS event arrives within 5s of spinner start, rotate generic personality lines ("Pondering...", "Cross-referencing...") so the spinner never looks frozen.

**Backend (agent-side) implementation:**
- Add `soto_agent/sf_publish.py` — `publish_status(correlation_id, stage, **kwargs)` helper. Reuses the OAuth client_credentials pattern from existing middleware.
- Call from `run_agent` between turns AND from inside tool dispatch (before each `wiki_search`/`wiki_read` actually fires).
- Status PE failures must NOT abort the agent loop (best-effort fire-and-forget; log but continue).

**Cost / governor checks:**
- Org default: 250k high-volume PE / 24h. Demo scale (~10 questions × ~6 stages) = trivial.
- Each PE publish ≈ 50-100ms on agent side. ~5 stages per question = +250-500ms total latency. Worth it for perceived-latency win.
- Order: PEs fire in publish order; SF empApi delivers in order. No sequence-number field needed for v1.

**Implementation timing:** Build during step 7 (Tue 5/12 SF integration). LWC changes pair with that work — coordinate with Salesforce engineer to add the PROGRESS branch to existing `accountIntelligence` LWC.

**Future tiers (deferred):**
- Path B (chunked answer per sentence) — only if A insufficient. Would emit additional PEs with answer fragments.
- Path C (SSE direct LWC ↔ Container App) — post-demo. New CSP Trusted Site + auth model.

## Architecture decisions (locked this session 2026-05-09)

| Decision | Choice | Reason |
|----------|--------|--------|
| Web framework | **FastAPI** (not Flask) | Async, Pydantic, native SSE for streaming stretch |
| Agent host | **Azure Container App** (not Function App) | No 230s ceiling; agent-loop friendly; future SSE |
| Agent loop | **Self-hosted Python** (not Foundry Agent Service) | Learning value; Ed Donner pattern; full control |
| LLM (v1 prototype) | **Foundry `gpt-4.1-mini`** | BBC-tenant; compliance-cleared. Prototype only — plan to eval `gpt-5` family, `deepseek`, `claude-sonnet-4.x` post-demo behind a model-name env var. Keep prompts model-agnostic where possible. |
| Genie role | **Tool, not primary path** | Demoted 5/8. May call when NL is fuzzy; agent writes direct SQL via Databricks MCP otherwise. A/B eval post-demo. |
| SF round-trip | **Reuse existing Function App + PE channel** | PR 15651 shipped the durable contract — don't rebuild |
| Vocabulary | **3-layer**: system-prompt primer + `glossary_lookup` tool + `wiki_search`/`wiki_read` tools | Cuts tool calls for common terms; precise lookup when needed |
| Streaming UX | **Path A first**: status-step PE → chunked PE (B) → SSE direct (C) | Stay in PR 15651 contract for v1 demo. Agent publishes 2-3 status PEs per query ("searching", "drafting", "done"). Path B/C only if A insufficient. |

### System prompt / token budget reasoning

Four real constraints on system-prompt size — track only the binding one for the
current model:

1. **Cost** — input tokens per turn × turns. `gpt-4.1-mini` ≈ $0.0001/1K input. 1.2K-token primer × thousands of demo turns = pennies. Not binding at v1.
2. **Context window** — `gpt-4.1-mini` = 128K. System prompt + tool schemas + conversation + tool results all share. 1-2K of system prompt = trivial. Not binding.
3. **First-token latency** — minor. ~tens of ms diff for 1K vs 5K tokens. Not binding at this scale.
4. **Attention dilution** — biggest real risk. Frontier models start to ignore buried instructions when system prompt approaches ~5K tokens. **Working budget: keep total system prompt ≤2K, hard ceiling 5K total (system prompt + tool schemas).**

Current breakdown (v0.1, measured 2026-05-08):
- Identity + How-to-answer + Tool rules + Vocabulary primer + Disambiguation block (single `system_prompt.md` file): ~1.5K tokens (was ~1.2K before disambiguation/comparison/efficiency rules added)
- Tool schemas in code (currently 2 tools — `wiki_search`, `wiki_read`): ~250 tokens
- **Total ≈ 1.75K tokens.** Will grow when `glossary_lookup` (~150), `databricks_query` (~250), `salesforce_query` (~250) added → projected ~2.4K. Still under 5K hard ceiling.
- Revisit if eval shows tool-selection drift or instruction-skip.

Industry reference points: Cursor ~3K, ChatGPT ~2K, Claude.ai ~5K. We're in normal range.

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
| ~~`glossary_lookup` reads file on disk OR loaded into memory at boot?~~ | **Resolved 2026-05-12: boot-load.** File is 137 lines + stable. Parsed once at import; cached in module-level dicts. |
| Vocabulary primer compression: hand-curate OR LLM-generate from glossary? | Resolved 2026-05-08: hand-curated v0.1 at ~1.2K tokens (no compression — under attention-dilution ceiling). Revisit only if eval shows tool-selection drift. |
| Cross-model eval: `gpt-5` family, `deepseek`, `claude-sonnet-4.x` vs `gpt-4.1-mini` | Post-demo. Add model name as env var so swap is config-only. Keep prompts model-agnostic. |
| Genie space tuning vs raw MCP for direct SQL — which wins on what query types? | Eval Mon 5/12 + post-demo |
| AI Search semantic ranker as 4th tool? | Wed 5/14 (after wiki vs AI Search eval) |
| Path B (chunked PE per sentence) needed, or does Path A suffice? | After 5/20 dry-run feedback |
| Path C (SSE direct LWC ↔ Container App)? | Post-demo. New CSP Trusted Site + auth model. |

## Build order (REVISED 2026-05-08 — spine before tools)

1. ✅ **Wiki primitives** — `wiki_search` + `wiki_read` in `tools/wiki.py`. Done 2026-05-08. (Patched 2026-05-12: selector prompt hardened + basename rglob fallback after `Entities/` folder hallucination.)
2. ✅ **Vocabulary primer** — `prompts/system_prompt.md`, ~1.2K tokens hand-curated. Done 2026-05-08.
3. ✅ **Agent loop skeleton** — `soto_agent/app.py` with `run_agent`, `_MODEL_BUILDERS` registry, tool dispatch, while-loop until no tool_calls. Done 2026-05-08.
4. **Glue tools to loop:**
   - 4a. ✅ `glossary_lookup` (Tue 5/12). User wrote function + Pydantic + TOOLS/_DISPATCH; Claude wrote parser glue.
   - 4b. ⬜ `databricks_query` — Wed-Thu (after step 7 spine lands).
   - 4c. ⬜ `salesforce_query` — Thu-Fri.
5. ✅ **FastAPI route** — `soto_agent/server.py`, `POST /soto-agent` returning `{answer: str}`. Tue 5/12. Needs `/health` added before Container App probes.
6. **Azure deploy — split:**
   - 6a. ✅ Dockerfile + slim `requirements.txt` + `.dockerignore` + Makefile orchestration. First image `bbcsotoacr.azurecr.io/soto-agent:latest` pushed via `az acr build`. Tue 5/12.
   - 6b. ⬜ `az containerapp create` — Wed 5/13. Wires secrets + env vars + ingress + probes.
7. ⬜ **SF integration** — Named Credential URL swap to deployed Container App. Wed 5/13 PM (depends on 6b returning an FQDN).

**Re-order rationale:** Step 4 (rest of tools) shifted AFTER 5-6-7 so SF integration spine is live by Tue 5/12. Adding tools later = no SF-side changes. See "Where we left off" section above for the full revised week timeline.

## Repo layout (actual, end of 2026-05-12)

```
/Users/brooksjohnson/ai-engineering/soto_agent/
├── __init__.py
├── app.py                    # agent loop entry + CLI; run_agent(question, ...)
├── server.py                 # FastAPI POST /soto-agent (wraps run_agent)
├── Dockerfile                # python:3.12-slim image; CMD = uvicorn server:app
├── requirements.txt          # slim runtime deps (openai/pydantic/fastapi/uvicorn/dotenv)
├── Makefile                  # test / refresh-glossary / vault / prep / image / deploy / run / clean
├── CONTEXT.md                # this file
├── tools/
│   ├── __init__.py
│   ├── wiki.py               # wiki_search + wiki_read (done)
│   ├── glossary_lookup.py    # glossary_lookup (done)
│   ├── databricks_query.py   # (planned Wed 5/13)
│   └── salesforce_query.py   # (planned Thu-Fri)
├── prompts/
│   └── system_prompt.md      # vocabulary primer + agent instructions
├── scripts/
│   ├── __init__.py
│   └── build_vault_subset.py # filters local Obsidian vault -> data/vault/
├── tests/
│   ├── __init__.py
│   └── test_glossary_lookup.py  # 19 pytest cases
├── evals/
│   ├── __init__.py
│   ├── run_evals.py
│   ├── test_cases.jsonl
│   └── runs/
└── data/                     # baked-in container data (vault subset is gitignored)
    ├── ubiquitous-language.md   # committed copy; refreshed via Makefile
    └── vault/                   # 1600 .md files + filtered index.md (build artifact)
```

Plus repo-root assets: `.dockerignore`, `.gitignore` (with `soto_agent/data/vault/` entry).

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
