"""Databricks query tools for the SOTO agent.

Two tools wired to the agent:
- `execute_sql(query)`: run a read-only SQL statement against the BBC
  Databricks Serverless SQL Warehouse and return rows + column metadata.
- `get_depletion_schema()`: return a curated schema doc covering the 3 key
  `dev.depletion` tables used in the SOTO Situation step. Agent calls this
  before forming SQL so it knows what's available without re-describing tables
  every turn.

Auth: Databricks SDK WorkspaceClient auto-detects from env vars
  DATABRICKS_HOST + DATABRICKS_TOKEN. Warehouse id from
  DATABRICKS_WAREHOUSE_ID.

This module is intentionally thin — no caching, no warehouse-start logic.
For v1 demo we assume the warehouse is warm (or accept cold-start latency on
first call). Cold-start handling can move into a tool wrapper if needed.
"""

from __future__ import annotations

import os
import time
from datetime import timedelta
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

load_dotenv()

_WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]
_GENIE_SPACE_ID = os.environ.get("DATABRICKS_GENIE_SPACE_ID", "")
_client = WorkspaceClient()  # picks up DATABRICKS_HOST + DATABRICKS_TOKEN

# Genie config — mirrors the working bbc-sf-middleware Azure Function pattern.
_GENIE_WAIT_TIMEOUT_S = int(os.environ.get("GENIE_WAIT_TIMEOUT_SECONDS", "120"))
_GENIE_QUERY_EXEC_TIMEOUT_S = int(os.environ.get("GENIE_QUERY_EXEC_TIMEOUT_S", "60"))
_GENIE_POLL_INTERVAL_S = 2
_GENIE_MAX_ROWS = 50


class SqlResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


# Curated schema for SOTO Situation step. Hand-written rather than generated
# because the agent benefits from English use-case framing, not raw column
# dumps. Update when materially new fields land in the lakehouse.
_DEPLETION_SCHEMA_DOC = """
# Databricks `dev.depletion` schema — for SOTO Situation step

You have read-only access to these tables via `execute_sql(query)`.
All tables are in catalog `dev`, schema `depletion`. Use fully-qualified names.

## CRITICAL RULES (read before writing any SQL)

1. **Call this tool FIRST** every session, BEFORE `execute_sql`. Do not guess
   column names — case-sensitive Databricks SQL will reject hallucinated
   columns. The error suggestions list is your safety net, but a wasted turn.

2. **Anchor date filters to `MAX(dtSalesWeekEnd)`, NOT `current_date()`.**
   This lakehouse has ingestion lag (often weeks to months). Use:
       `WHERE dtSalesWeekEnd >= (SELECT MAX(dtSalesWeekEnd) FROM ...) - INTERVAL 4 WEEKS`
   or fetch latest date first with a small probe query, then filter relative
   to that. `current_date() - INTERVAL N WEEKS` will frequently return zero rows.

3. **Aggregate before comparing distributors.** `fact_depletionweeklyvariance`
   can contain multiple rows per `(distID, dtSalesWeekEnd)` due to within-
   distributor breakouts. For distributor-level totals:
       `GROUP BY distID, DistributorName, dtSalesWeekEnd` + `SUM(WeeklyUnitQty)`
   Single-row queries that don't group will mislead.

4. **Always `LIMIT`.** Default 50. Lakehouse can return millions of rows.

---

## `dev.depletion.fact_depletionweeklyvariance` — distributor trend signals (PREFERRED)

Pre-aggregated weekly metrics per distributor with anomaly detection already
computed. Best table for "is this distributor up/down vs peers?" questions.

Columns (key ones):
- `distID` (string)          — distributor code (e.g. `441SUP`)
- `DistributorName` (string) — human name (e.g. `Superior Beverage Group (Glenwillow)`)
- `dtSalesWeekEnd` (date)    — week ending date
- `WeeklyUnitQty` (decimal)  — units depleted that week
- `WeeklyGrandTotal` (decimal) — total units across all distributors that week
- `PercentOfBiz` (decimal)   — this distributor's share of total business that week
- `PercOfBiz_25wkAVG`        — 25-week rolling average of PercentOfBiz
- `PercOfBiz_25wkSTD`        — 25-week std dev
- `PercOfBiz_25wkZSCORE`     — z-score vs 25-week window (|Z|>2 = anomaly)
- `PercOfBiz_52wkAVG`, `PercOfBiz_52wkSTD`, `PercOfBiz_52wkZSCORE` — 52-week equivalents
- `WeeklyUnitQty_13WkAVG`    — 13-week rolling average of unit qty

**Use for:** trend assessment, peer-relative performance, anomaly flags.

---

## `dev.depletion.vw_fact_depletion` — granular depletion facts

Per-day fact view at product × distributor × store level. Surrogate-key heavy
(DLKey pattern). Most columns are foreign keys to dim tables — joins required
for human-readable output. Use ONLY when weekly variance table can't answer.

Columns (key ones):
- `depletionDLKey` (bigint)    — surrogate PK
- `distDLKey` (int)            — FK to distributor dim
- `productDLKey` (int)         — FK to product dim
- `calendarDLKey` (int)        — FK to calendar dim
- `iUnitQty` (decimal)         — units sold
- `mNetPrice`, `mGrossNet`     — pricing measures
- `mCaseEquivalence` (decimal) — case-equivalent units
- `dtEffectiveStartDate` (date), `dtEffectiveEndDate` (date)

**Use for:** product-level depletion drill-down, daily granularity needs.
Default to the weekly variance table when the question is distributor-level.

---

## `dev.depletion.fact_market_depletion_bbc` — market/retail context

BBC's view of category sell-through in market (retail/on-premise), aggregated
by geo + channel + period. Use for "is the category down or just our
distributor?" market-context questions.

Columns (key ones):
- `SupplierCode`, `SupplierDesc`        — BBC vs competitor labels
- `ProductSegmentCode`, `ProductSegmentDesc` — category breakouts
- `ChannelCode`, `ChannelDesc`          — sales channel
- `PremiseTypeDesc`                     — on-premise vs off-premise
- `ChainFlag`                           — chain account indicator
- `State`, `CountyDesc`, `ZipCode`      — geo
- `Period` (int)                        — period code (4-week or fiscal — confirm before use)
- `Sales` (decimal)                     — sales measure (units? dollars? confirm)

**Use for:** market-context framing, geographic performance, category share.

---

## SQL conventions for this lakehouse

- All tables EXTERNAL DELTA — read-only is safe, no `LOCK` semantics needed
- Use `LIMIT` on every query — default 50 unless asked otherwise
- Date filters: `dtSalesWeekEnd >= current_date() - INTERVAL 13 WEEKS` style
- Column names ARE case-sensitive in Databricks SQL — use exact casing above
"""


def execute_sql(query: str, *, max_rows: int = 50) -> SqlResult:
    """Run a read-only SQL statement on the configured warehouse.

    Args:
        query: SQL string. Read-only. No DDL or DML.
        max_rows: Truncate result set to this many rows. Default 50.

    Returns:
        SqlResult with columns, rows, row_count, truncated flag.
    """
    resp = _client.statement_execution.execute_statement(
        warehouse_id=_WAREHOUSE_ID,
        statement=query,
        wait_timeout="30s",
    )

    # If still running after wait_timeout, poll briefly.
    statement_id = resp.statement_id
    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        resp = _client.statement_execution.get_statement(statement_id)

    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        err = resp.status.error
        msg = err.message if err else "unknown error"
        raise RuntimeError(f"Databricks SQL failed: {msg}")

    manifest = resp.manifest
    columns = [c.name for c in (manifest.schema.columns if manifest and manifest.schema else [])]
    raw_rows = (resp.result.data_array if resp.result else []) or []

    truncated = len(raw_rows) > max_rows
    rows = raw_rows[:max_rows]

    return SqlResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
    )


def get_depletion_schema() -> str:
    """Return a curated schema doc for the depletion tables.

    Call this BEFORE writing SQL against `dev.depletion.*` so you know which
    table answers which kind of question. Cached at import time — cheap to call.
    """
    return _DEPLETION_SCHEMA_DOC


class GenieResult(BaseModel):
    """Result of an `ask_genie` call.

    `text` is Genie's natural-language reply (may include clarifying questions).
    `sql_query` is the SQL Genie generated to answer (empty if it didn't write SQL).
    `columns` / `rows` are the executed-query results (empty if SQL didn't run).
    `conversation_id` lets a caller make follow-ups via Genie if we wire that.
    """

    text: str = ""
    sql_query: str = ""
    columns: list[str] = []
    rows: list[list[Any]] = []
    conversation_id: str = ""
    error: str = ""


def ask_genie(question: str) -> GenieResult:
    """Ask the BBC Sales Enablement Genie space a natural-language question.

    Use this for fuzzy questions where you can't easily form SQL — e.g. "How is
    Brand X selling in markets where Competitor Y just launched?". Genie has
    curated table knowledge for the configured space; it can pick the right
    tables and form joins you might miss with `execute_sql`.

    For questions you can answer with the 3 depletion tables in
    `get_depletion_schema`, prefer `execute_sql` — it's faster and gives you
    full control. Reach for Genie when you need its curated semantic model.

    Returns a `GenieResult` with text + generated SQL + result rows.
    """
    if not _GENIE_SPACE_ID:
        return GenieResult(error="DATABRICKS_GENIE_SPACE_ID env var not set.")

    try:
        wait = _client.genie.start_conversation(
            space_id=_GENIE_SPACE_ID, content=question
        )
        message = wait.result(timeout=timedelta(seconds=_GENIE_WAIT_TIMEOUT_S))
    except Exception as e:
        return GenieResult(error=f"start_conversation failed: {e}")

    conversation_id = getattr(message, "conversation_id", "") or ""
    message_id = getattr(message, "id", "") or ""

    text = ""
    sql_query = ""
    for att in (message.attachments or []):
        if getattr(att, "text", None) and att.text and not text:
            text = getattr(att.text, "content", "") or ""
        if getattr(att, "query", None) and att.query and not sql_query:
            sql_query = getattr(att.query, "query", "") or ""

    columns: list[str] = []
    rows: list[list[Any]] = []
    err = ""

    if sql_query:
        try:
            exec_resp = _client.genie.execute_message_query(
                space_id=_GENIE_SPACE_ID,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            statement = exec_resp.statement_response
        except Exception as e:
            err = f"execute_message_query failed: {e}"
            statement = None

        if statement and statement.statement_id:
            statement_id = statement.statement_id
            deadline = time.time() + _GENIE_QUERY_EXEC_TIMEOUT_S
            while True:
                state = (
                    statement.status.state.value
                    if statement.status and statement.status.state
                    else None
                )
                if state == "SUCCEEDED":
                    if statement.manifest and statement.manifest.schema:
                        columns = [
                            c.name
                            for c in (statement.manifest.schema.columns or [])
                            if c.name
                        ]
                    if statement.result and statement.result.data_array:
                        rows = statement.result.data_array[:_GENIE_MAX_ROWS]
                    break
                if state in ("FAILED", "CANCELED", "CLOSED"):
                    err = (
                        statement.status.error.message
                        if statement.status and statement.status.error
                        else f"Genie SQL terminal state {state}"
                    )
                    break
                if time.time() >= deadline:
                    err = f"Genie SQL poll timeout after {_GENIE_QUERY_EXEC_TIMEOUT_S}s"
                    break
                time.sleep(_GENIE_POLL_INTERVAL_S)
                statement = _client.statement_execution.get_statement(statement_id)

    return GenieResult(
        text=text,
        sql_query=sql_query,
        columns=columns,
        rows=rows,
        conversation_id=conversation_id,
        error=err,
    )
