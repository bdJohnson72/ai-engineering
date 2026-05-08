# SOTO Agent — Vocabulary Primer (v0.1)

> ~700-token primer baked into the outer agent's system prompt. Common BBC sales
> terms covered here so the agent doesn't burn tool calls looking them up.
> Use `glossary_lookup` for terms NOT in this primer (rare roles, niche objects,
> activity prefixes, RecordType deep-dives).

---

## Roles

- **Account Caller** — field sales rep visiting retail accounts daily.
- **Sales Manager** — district/area/region manager overseeing a territory and its callers. Also called **Territory Owner** when bound to a specific geography.
- **Call Point Caller** — Key Account Specialist for chain/national accounts.

## Core Salesforce objects (with API names where disambiguation matters)

- **Account** — Salesforce Account record. RecordTypes: `Call Point` (retailer), `Wholesaler` (distributor), `Off-Premise Retailer`.
- **Account Visit** — a scheduled or completed store visit by a rep.
- **Visit Job** (`cgcloud__Visit_Job__c`) — an in-visit task or answer point. **Not** the same as a Retailer Objective.
- **Retailer Objective (RO)** (`cgcloud__Account_Task__c`) — account-level task/objective. Most overloaded term in the codebase. Always say "RO," never bare "Account Task."
- **Promotion** (`cgcloud__Promotion__c`) — generic parent object. The business concepts are:
  - **Wholesaler Program (WSP)** — RecordType `Wholesaler_Program`. Promo negotiated with a wholesaler.
  - **Chain Program** — RecordType `SellablePromotion`. Promo targeting chain retailer accounts.
- **Tactic** — child of Promotion; selling objective inside a WSP or Chain Program.
- **Tactic Product** — junction linking a Tactic to specific products.
- **Trip List** — weekly visit routing plan; the rep's planned accounts.
- **Depletion Volume** — product sales volume by account/period; the source of truth for "is this product selling here?"
- **Smart Recommendation (Smart Rec)** — algorithmically generated selling opportunity for a rep.
- **MOB Objective** — territory-level selling target set manually by a District Manager.

## RO sources (always specify which)

Retailer Objectives come from exactly four sources:

1. **MOB** — Manual Objectives from District Managers, cascaded to account ROs.
2. **COT Priority** — Priority SKU recommendations matched by Class of Trade.
3. **Chain Mandate** — Chain Program targets cascaded via FAH.
4. **Smart Rec** — Algorithmic, depletion-driven opportunities.

## Selling process

- **PRIME** — BBC's core selling process: **Prepare → Research → Improve → Make the sale → Execute**. Used at every store visit.
- **SOTO** — **Situation, Objectives, Tools, Objections.** The pre-visit prep framework used in PRIME's Prepare step. (Also the name of this agent.)

## Industry context

- **Three-Tier System** — beer distribution: BBC (manufacturer) → Wholesaler/Distributor → Retailer. Legally mandated in most U.S. states.
- **On-Premise** — bars, restaurants, nightclubs (drinks served on-site).
- **Off-Premise** — stores, liquor shops, grocery (packaged for off-site consumption).
- **Priority SKU** — ~15 nationally prioritized products curated by leadership. Tracked via Recommendation ROs scored Available (selling) or Gap (opportunity).
- **Class of Trade (COT)** — account classification (9 On-Premise, 10 Off-Premise types). Filters product eligibility and tactic templates.
- **Circana** — primary beer industry scan-data provider (formerly IRI). **Off-premise only** — no on-premise coverage.
- **MULO+C** — Multi-Outlet + Convenience. Circana's largest off-premise dataset (grocery, mass, club, c-stores).
- **Rate of Sale** — per-store-per-week velocity from Circana. Used for launch tracking and SKU performance.

## Critical disambiguations — always qualify

- **"Objective"** is overloaded. Always say one of: **Tactic Objective** (selling intent on a Tactic), **Selling Objective RO** (an Account_Task RecordType), or **MOB Objective** (territory goal).
- **"Promotion"** — use **WSP** or **Chain Program** for business concepts. Reserve "Promotion" for the raw `cgcloud__Promotion__c` parent.
- **"Visit"** alone is ambiguous. Use **Account Visit** (the record), **Visit Job** (in-visit task), **Visit Template** (configuration), or "the act of visiting."
- **"Survey"** — always prefix the type: **B.A.S.E. Survey**, **Display Survey**, or **EOD Survey**.
- **"Activity"** in this codebase almost always means a CG Cloud **Activity Template**. Use that phrase, or "Salesforce Task/Event" if you mean the standard activity record.

---

## When to call `glossary_lookup`

- Activity prefixes (DIST, FEAT, DISP, POS, RESET, CONV, DQA, OOC).
- Less-common objects (Flatten Account Hierarchy, Customer Set, Promotion Store, EOD Survey).
- Wholesaler/Distributor terminology (Distributor House, A-B house, etc.).
- Any role not listed above (Wholesaler Manager, Business Admin, IT Admin).
- RecordType-level detail beyond what's listed here.

When the question hinges on a precise definition, lookup is cheap — call it.
