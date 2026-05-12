# Ubiquitous Language

Last updated: 2026-04-14

Domain terminology glossary for the BBC NGST/CG Salesforce codebase. When these terms appear in Jira stories, code reviews, or conversations, use the canonical term and definition below.

---

## People & Roles

| Term                   | Definition                                                                                               | Aliases to Avoid                                                          |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Account Caller**     | Field sales rep who visits retail accounts daily to execute visit tasks and sell products                | Sales rep, field rep, caller, brewery rep                                 |
| **Call Point Caller**  | Key Account Specialist managing chain/national accounts with complex multi-location visits               | Key account rep, chain rep                                                |
| **Wholesaler Manager** | Market Channel Manager coordinating promotional programs between BBC and wholesaler/distributor partners | Channel manager, market manager                                           |
| **Sales Manager**      | District/Area/Region Manager overseeing territory performance and team activity                          | DM, district manager, territory manager (ambiguous — see Territory Owner) |
| **Territory Owner**    | The Sales Manager assigned to a specific geographic territory in the org hierarchy                       | Territory manager, TM (overlaps with Sales Manager)                       |
| **Business Admin**     | Sales Training or Business Admin managing system configuration and supporting field teams                | Admin, sysadmin (too generic)                                             |
| **IT Admin**           | IT or Production Support managing system health, deployments, and integrations                           | Prod support, IT                                                          |

## Salesforce Objects

| Term                                | Definition                                                                                                                             | Aliases to Avoid                                                             |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Account**                         | Salesforce Account record; RecordTypes: `Call Point` (retailer), `Wholesaler` (distributor), `Off-Premise Retailer`                    | Store (ambiguous), location, customer                                        |
| **Account Visit**                   | `cgcloud__Account_Visit__c` — a scheduled or completed store visit by a rep                                                            | Visit (ambiguous — could mean Visit Job or Visit Template)                   |
| **Visit Job**                       | `cgcloud__Visit_Job__c` — an in-visit task or answer point within an Account Visit                                                     | Account Task (conflicts with cgcloud**Account_Task**c), job                  |
| **Retailer Objective (RO)**         | `cgcloud__Account_Task__c` — account-level task/objective; the canonical name for all RecordTypes                                      | Account Task (too generic), objective (overloaded — see Flagged Ambiguities) |
| **Promotion**                       | `cgcloud__Promotion__c` — CG Cloud parent object for promotional programs; RecordTypes determine the business type                     | Program (too vague), promo                                                   |
| **Wholesaler Program (WSP)**        | `cgcloud__Promotion__c` with RecordType `Wholesaler_Program` — promotional program negotiated with a wholesaler distributor            | Promotion (overloaded), program                                              |
| **Chain Program**                   | `cgcloud__Promotion__c` with RecordType `SellablePromotion` — promotional program targeting chain retailer accounts                    | Chain Promotion, sellable promotion                                          |
| **Tactic**                          | `cgcloud__Tactic__c` — child of Promotion; represents a selling objective within a WSP or Chain Program                                | Objective (overloaded), selling target                                       |
| **Tactic Product**                  | `cgcloud__Tactic_Product__c` — junction linking a Tactic to Product2 records                                                           | Product assignment                                                           |
| **Promotion Store**                 | `cgcloud__Promotion_Store__c` — per-account instance of a Chain Program created via FAH cascade                                        | Store instance, chain store record                                           |
| **Trip List**                       | `cgcloud__Trip_List__c` — weekly visit routing plan containing accounts to visit                                                       | Trip, visit route, route                                                     |
| **Flatten Account Hierarchy (FAH)** | `cgcloud__Flatten_Account_Hierarchy__c` — denormalized hierarchy tree enabling efficient descendant queries                            | Account hierarchy, FAH                                                       |
| **Depletion Volume**                | `NGST_Depletion_Volume__c` — product sales volume data by account and time period; source of truth for "is this product selling here?" | Depletion, volume data                                                       |
| **Smart Recommendation**            | `NGST_Smart_Recommendation__c` — algorithmically generated selling opportunity for a rep                                               | Smart Rec                                                                    |
| **MOB Objective**                   | `NGST_MOB_Objective__c` — territory-level selling target set manually by a District Manager                                            | MOB, manual objective, DM objective                                          |
| **EOD Survey**                      | `NGST_EOD_Survey__c` — End-of-Day manager feedback form on field activities; 7 RecordTypes                                             | End of Day Survey, EOD                                                       |

## Business Domains

| Term                            | Definition                                                                                                                                  | Aliases to Avoid                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **PRIME**                       | BBC's core selling process framework defining rep activities at each step of a store visit                                                  | PRIME selling, the process                          |
| **SOTO**                        | Internal BBC sales methodology (details not surfaced in Salesforce UI)                                                                      | —                                                   |
| **B.A.S.E. Survey**             | Brand, Availability, Shelf position, Eye-level — product compliance questionnaire for off-premise retailers                                 | BASE Survey, base survey, brand survey              |
| **Display Survey**              | In-store display compliance tracking for point-of-sale materials and shelf placement                                                        | Compliance survey (too generic)                     |
| **Priority SKU**                | ~15 nationally prioritized products curated by leadership; tracked via Recommendation ROs with Available/Gap scoring                        | Priority product, key SKU                           |
| **Class of Trade (COT)**        | Account classification by retail type (9 On-Premise, 10 Off-Premise types); filters product eligibility and tactic templates                | Account type (too generic), trade class             |
| **On-Premise**                  | Bars, restaurants, nightclubs — establishments serving drinks for on-site consumption                                                       | On-prem, on premise                                 |
| **Off-Premise**                 | Stores, liquor shops, grocery — retailers selling packaged goods for off-site consumption                                                   | Off-prem, off premise                               |
| **Anchor Account**              | Parent account in a Chain Program hierarchy; starting point for Promotion Store cascade via FAH                                             | Parent account (too generic in hierarchy context)   |
| **Customer Set**                | Collection of accounts targeted by a Chain Program; managed via `cgcloud__Account_Set_Account__c` junction                                  | Account Set, account group                          |
| **Management Chain**            | User hierarchy for EOD Survey email routing — from direct manager up to VP level                                                            | Reporting chain, hierarchy                          |
| **Three-Tier System** (new)     | The beer distribution model: Manufacturer (BBC) → Wholesaler/Distributor → Retailer; legally mandated in most U.S. states                   | Distribution chain, supply chain (too generic)      |
| **SOTO** (new)                  | Situation, Objectives, Tools, Objections — pre-visit preparation framework used in the **Prepare** step of PRIME                            | —                                                   |
| **Zone** (new)                  | Physical area of a retail account (0=website, 1=exterior, 2=floor/backroom, 3=shelf/cooler or back-of-bar); used during PRIME Research step | Area, section                                       |
| **Call Recap** (new)            | Post-visit record of accomplishments and account updates; the **Execute** step of PRIME                                                     | Visit summary, visit notes                          |
| **Standard Activity** (new)     | Recurring visit task performed at every visit (e.g., freshness check, shelf survey); contrast with **Event-Driven Activity**                | Regular task, default activity                      |
| **Event-Driven Activity** (new) | Promotion-linked visit task triggered by a Chain Program or specific campaign; contrast with **Standard Activity**                          | Promo activity, campaign task                       |
| **Circana** (new)               | Primary beer industry scan data provider (formerly IRI + NPD); off-premise only — no on-premise sales captured                              | IRI (legacy name)                                   |
| **MULO+C** (new)                | Multi-Outlet + Convenience — Circana's largest off-premise data set covering grocery, mass, club, and c-stores                              | —                                                   |
| **Rate of Sale** (new)          | Per-store, per-week velocity metric from Circana; used for launch tracking and SKU performance evaluation                                   | Velocity, turns                                     |
| **Distributor House** (new)     | A wholesaler operation aligned with a specific supplier (e.g., "A-B house" = Anheuser-Busch aligned distributor)                            | Wholesaler (too generic — doesn't convey alignment) |

## Retailer Objective Sources (4 Types)

Retailer Objectives come from exactly four sources. Always specify which:

| Source            | Description                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------ |
| **MOB**           | Manual Objectives set by District Managers — territory-level goals cascaded to account ROs |
| **COT Priority**  | Priority SKU Recommendations matched to account COT via Product Listing Modules            |
| **Chain Mandate** | Chain Program targets generated from Promotion Store cascade                               |
| **Smart Rec**     | Algorithmically generated opportunities from depletion data and account profile            |

## Retailer Template Prefixes

Activity types for Retailer Objectives, each mapping to an email template and Account Task Template:

| Prefix    | Meaning                                 |
| --------- | --------------------------------------- |
| **DIST**  | New Distribution                        |
| **FEAT**  | Features (product education)            |
| **DISP**  | Display (point-of-sale)                 |
| **POS**   | POS: High Impact (premium placement)    |
| **RESET** | Cooler Reset                            |
| **CONV**  | Convert Seasonal (seasonal → permanent) |
| **DQA**   | Distributor Quality Audit               |
| **OOC**   | Out of Code (stale product)             |

## Relationships

- A **Territory Owner** (Sales Manager) manages multiple **Account Callers**
- An **Account Caller** follows a **Trip List** to conduct **Account Visits** at **Accounts**
- During an **Account Visit**, the rep completes **Visit Jobs** and works on **Retailer Objectives (ROs)**
- **Wholesaler Programs (WSPs)** contain **Tactics** which contain **Tactic Products**
- **Chain Programs** cascade **Promotion Stores** to descendant **Accounts** via **FAH**
- **Priority SKUs** generate **Recommendation ROs** scored as Available (selling) or Gap (opportunity)
- **MOB Objectives** cascade from territory level to individual account **ROs**
- **EOD Surveys** trigger email notifications up the **Management Chain**
- The **Three-Tier System** flows: BBC (manufacturer) → **Wholesaler/Distributor** → **Retailer** (On-Premise or Off-Premise)
- An **Account Visit** follows the **PRIME** process: Prepare (**SOTO**) → Research (**Zones**) → Improve → Make the Sale → Execute (**Call Recap**)
- Visit tasks are either **Standard Activities** (recurring) or **Event-Driven Activities** (promotion-linked)
- **Circana** provides off-premise scan data (**MULO+C**, **Rate of Sale**); no on-premise coverage

## Example Dialogue

> **PM:** "The rep needs to see their promotions on the visit screen."
> **Dev:** "Do you mean **Wholesaler Programs (WSPs)** or **Chain Programs**? They're different RecordTypes on `cgcloud__Promotion__c`."
> **PM:** "WSPs — the ones the wholesaler manager creates."
> **Dev:** "Got it. And by 'rep' you mean **Account Caller**, right? Not the **Call Point Caller** who handles chain accounts?"
> **PM:** "Account Caller. They should see the **Tactics** and **Tactic Products** for their territory."
>
> **Dev:** "This story says 'update the objective when the product is found.' Which objective?"
> **PM:** "The one on the account — where the rep marks it complete."
> **Dev:** "That's a **Retailer Objective (RO)** — `cgcloud__Account_Task__c`. Which RO source? **MOB**, **COT Priority**, **Chain Mandate**, or **Smart Rec**?"
> **PM:** "The priority SKU one."
> **Dev:** "OK — that's a **Recommendation RO** from the **COT Priority** source. We'd update its status from Gap to Available based on **Depletion Volume** data."

## Flagged Ambiguities

- **"Objective"** is the most overloaded term in this codebase. It can mean: (1) a field on `cgcloud__Tactic__c` describing selling intent, (2) a `cgcloud__Account_Task__c` RecordType called "Selling Objective," (3) an `NGST_MOB_Objective__c` territory-level goal. **Always qualify**: "Tactic Objective," "Selling Objective RO," or "MOB Objective."

- **"Promotion"** means two different things: (1) the CG Cloud managed object `cgcloud__Promotion__c` (generic parent), (2) the business concept of a Wholesaler Program or Chain Program. **Always use WSP or Chain Program** when referring to the business concept. Reserve "Promotion" for the raw Salesforce object.

- **"Account Task"** is the API name (`cgcloud__Account_Task__c`) but is easily confused with `cgcloud__Visit_Job__c` (also a "task" within a visit). **Use "Retailer Objective (RO)"** for Account Task records and **"Visit Job"** for in-visit tasks.

- **"Survey"** without a qualifier could mean BASE, Display, or EOD — three fundamentally different things. **Always prefix with the survey type.**

- **"Visit"** without context could mean `Account Visit` (the record), `Visit Job` (in-visit task), `Visit Template` (the configuration), or the act of visiting a store. **Use the full term.**

- **"Template"** is overloaded across at least 5 object types (Account Task Template, Visit Template, Job Template, Tactic Template, Email Template). **Always specify which template type.**

- **"Activity"** can mean: (1) a CG Cloud activity template grouping questions/surveys for visits, (2) a Salesforce Task/Event activity record, (3) the general act of doing something at an account. In this codebase, it almost always means (1). **Use "Activity Template"** when referring to the CG Cloud concept; use "Task" or "Event" for standard Salesforce activities.
