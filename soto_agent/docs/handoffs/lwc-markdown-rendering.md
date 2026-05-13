# Handoff: Render Markdown in `accountIntelligence` LWC

**Context.** The SOTO agent (Container App in Azure) now returns markdown-formatted answers in the `text` field of `Account_Intelligence__e.Result__c`. The current LWC renders it as a single `<p>` with the raw markdown characters (`**bold**`, `- bullet`, `\n`), which looks unformatted. We need to render it as styled HTML.

**Decision.** Use the standard client-side pattern: `marked.js` (markdown → HTML) + `DOMPurify` (sanitize HTML before injecting). Both ship as Salesforce static resources, loaded via `lightning/platformResourceLoader`. No server-side change required.

**Why not server-side conversion?** Tried that mentally — `lightning-formatted-rich-text` strips a lot (tables, code blocks, inline styles). marked + DOMPurify gives full markdown support and is the standard SF community approach.

---

## Step 1 — Download the libraries

Grab these two files:

| Library | Version | Download URL |
|---|---|---|
| marked | latest (~v12) | https://cdn.jsdelivr.net/npm/marked/marked.min.js |
| DOMPurify | latest (~v3.1) | https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js |

```bash
curl -L https://cdn.jsdelivr.net/npm/marked/marked.min.js -o marked.min.js
curl -L https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js -o purify.min.js
```

---

## Step 2 — Upload as static resources

Setup → Static Resources → New, twice:

| Resource Name | File | Cache Control |
|---|---|---|
| `marked` | `marked.min.js` | Public |
| `dompurify` | `purify.min.js` | Public |

Names matter — they're imported by name in the LWC.

---

## Step 3 — Update `accountIntelligence.html`

Replace the `<p class="...">{result.text}</p>` line with a manual-DOM div. `lwc:dom="manual"` is the only way LWC allows setting `innerHTML` directly (security policy).

```html
<template>
  <lightning-card title="Account Intelligence" icon-name="standard:einstein">
    <div class="slds-p-horizontal_medium">
      <lightning-button label="Get Depletion Summary" variant="brand" onclick={handleClick}></lightning-button>

      <template if:true={result}>
        <div data-id="result-card" class="slds-box slds-m-top_medium">
          <div lwc:dom="manual" data-id="answer" class="slds-text-body_regular slds-m-bottom_small"></div>
          <pre class="slds-text-body_small slds-text-color_weak slds-scrollable_x">{result.sqlQuery}</pre>
        </div>
      </template>

      <template if:true={timedOut}>
        <div data-id="timeout-card" class="slds-box slds-m-top_medium slds-theme_warning">
          <p class="slds-text-body_regular slds-m-bottom_small">
            Request timed out after 2 minutes. The summary may still arrive — try again to refresh.
          </p>
          <lightning-button label="Retry" variant="brand" onclick={handleRetry}></lightning-button>
        </div>
      </template>
    </div>
  </lightning-card>
</template>
```

---

## Step 4 — Update `accountIntelligence.js`

Two changes:

1. Import `loadScript` + the two static resources. Load them in `connectedCallback` (one-time).
2. In `handlePlatformEvent`, run the markdown text through `marked.parse(...)` → `DOMPurify.sanitize(...)` → write to the manual-DOM div's `innerHTML`.

```javascript
import { LightningElement, api } from "lwc";
import { subscribe } from "lightning/empApi";
import { loadScript } from "lightning/platformResourceLoader";
import MARKED from "@salesforce/resourceUrl/marked";
import DOMPURIFY from "@salesforce/resourceUrl/dompurify";
import queryAccountIntelligence from "@salesforce/apex/AccountIntelligenceController.queryAccountIntelligence";

const CHANNEL = "/event/Account_Intelligence__e";
const DEFAULT_QUERY = "Provide a summary of recent depletion trends for this account.";
const TIMEOUT_MS = 120000;

export default class AccountIntelligence extends LightningElement {
  @api recordId;
  correlationId;
  subscription;
  result;
  timedOut = false;
  _timeoutId;
  _libsLoaded = false;

  async connectedCallback() {
    if (this._libsLoaded) return;
    await Promise.all([loadScript(this, MARKED), loadScript(this, DOMPURIFY)]);
    this._libsLoaded = true;
  }

  generateCorrelationId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async handleClick() {
    this.timedOut = false;
    this.correlationId = this.generateCorrelationId();
    this.subscription = await subscribe(CHANNEL, -1, (msg) => this.handlePlatformEvent(msg));
    // eslint-disable-next-line @lwc/lwc/no-async-operation
    this._timeoutId = setTimeout(() => {
      this.timedOut = true;
      this.correlationId = null;
    }, TIMEOUT_MS);
    await queryAccountIntelligence({
      accountId: this.recordId,
      query: DEFAULT_QUERY,
      correlationId: this.correlationId,
    });
  }

  handleRetry() {
    return this.handleClick();
  }

  renderMarkdown(text) {
    if (!text) return "";
    // marked + DOMPurify are loaded as globals by loadScript
    // eslint-disable-next-line no-undef
    const rawHtml = marked.parse(text);
    // eslint-disable-next-line no-undef
    return DOMPurify.sanitize(rawHtml);
  }

  handlePlatformEvent(msg) {
    const payload = msg && msg.data && msg.data.payload;
    if (!payload || payload.CorrelationId__c !== this.correlationId) return;
    if (payload.Status__c === "SUCCESS") {
      const parsed = JSON.parse(payload.Result__c || "{}");
      this.result = { text: parsed.text || "", sqlQuery: parsed.sql_query || "" };
      if (this._timeoutId) {
        clearTimeout(this._timeoutId);
        this._timeoutId = null;
      }
      // Inject sanitized HTML into the manual-DOM div after render tick
      // eslint-disable-next-line @lwc/lwc/no-async-operation
      Promise.resolve().then(() => {
        const target = this.template.querySelector('[data-id="answer"]');
        if (target) target.innerHTML = this.renderMarkdown(this.result.text);
      });
    }
  }
}
```

---

## Step 5 — Optional CSS polish

Markdown HTML elements (`h1`, `ul`, `code`, `pre`, etc.) won't be styled by SLDS by default. Add a `.css` file in the LWC folder (`accountIntelligence.css`) if needed:

```css
[data-id="answer"] h1, [data-id="answer"] h2, [data-id="answer"] h3 {
  font-weight: 700;
  margin: 0.5em 0;
}
[data-id="answer"] ul, [data-id="answer"] ol {
  margin-left: 1.25em;
}
[data-id="answer"] code {
  background: #f4f4f4;
  padding: 0 4px;
  border-radius: 3px;
  font-family: monospace;
}
[data-id="answer"] table {
  border-collapse: collapse;
  margin: 0.5em 0;
}
[data-id="answer"] th, [data-id="answer"] td {
  border: 1px solid #ddd;
  padding: 4px 8px;
}
```

---

## Step 6 — Test

1. Deploy LWC + static resources to the UAT sandbox (`bostonbeer--uat01`).
2. Open an Account record (e.g., Buffalo Wild Wings used in earlier smoke).
3. Click "Get Depletion Summary."
4. Verify:
   - **Bold/italic** render styled (not as `**asterisks**`).
   - Bullet lists indent and render as `<ul>`.
   - Headings (`### Summary`) render larger/bolder.
   - No raw markdown characters visible.
5. Check browser console: no CSP errors from DOMPurify/marked load.

---

## Security note

`DOMPurify.sanitize(...)` strips dangerous HTML (script tags, event handlers, inline styles). This is the SF-approved pattern for rendering untrusted HTML in LWC. We're treating the agent's output as untrusted by default — defense in depth, even though the agent is server-controlled.

---

## Existing artifacts referenced

- Container App FQDN: `https://soto-agent.bluefield-26fe34d4.eastus.azurecontainerapps.io`
- Result__c JSON shape: `{text, sql_query, columns, rows, conversation_id, message_id}` (matches existing `GenieResult` contract from PR 15651).
- LWC subscriber filters by `CorrelationId__c` — already in place; no change needed.
- The agent emits markdown only in `text`. Other fields (`sql_query`, `columns`, `rows`) stay rendered as today (plain text / table — future when SQL paths land).
