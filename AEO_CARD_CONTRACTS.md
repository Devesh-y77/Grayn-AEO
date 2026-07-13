# AEO Block Kit Card Contracts

This document defines the JSON payload shape each of the six Grayn AEO MCP tools must return in order to render as a **premium Block Kit card** in Slack (instead of falling back to the plain-markdown renderer).

All renderers live in `supabase/functions/_shared/aeo-format.ts` under the "Grayn AEO backend v2 — JSON-first card renderers" section. They are invoked by:

- `slack-events-handler` — normal `@Grayn` mention flow (via `formatAeoMcpResult` → `renderAeoJsonCard`).
- `slack-interactions` — `aeo_next` button clicks (via `renderAeoJsonCard` directly in `handleAeoNext`).
- `aeo-job-runner` — background drain of `aeo_pending_jobs` (via `formatAeoMcpResult`).

## Contract rules that apply to every tool

1. **Response payload is the MCP tool's `content[0].text` string.** The renderer accepts:
   - a raw JSON object/array string, **or**
   - a fenced ` ```json … ``` ` block containing one.
   Anything that fails `JSON.parse` is treated as markdown and never crashes.
2. **Any of these shapes triggers the friendly "empty state" card** (with recovery buttons), no matter which tool was called:
   ```json
   { "error": "human readable message" }
   { "status": "error", "message": "…" }
   { "ok": false, "error": "…" }
   ```
   Optional `topic` and/or `engine` on the same object are used to build the recovery button (e.g. "Run a Live Scan on {topic}").
3. **All string values are truncated safely** (`truncate` helper) — passing long text will not break blocks, but Slack's Block Kit limits are:
   - `header.text.text`: ≤150 chars
   - `section.text.text`: ≤3000 chars (renderer caps at 2900)
   - `actions` block: ≤5 elements; `action_id`: ≤255 chars; button `value`: ≤2000 bytes (renderer caps `aeo_next` payloads at 1900).
4. **Numbers may be sent as `number` or numeric string** — the renderer coerces via `Number()`. Non-finite values render as `—`.
5. **Follow-up button routing.** Each card can emit `aeo_next` buttons whose `value` is `{"t": "<tool_name>", "a": {...args}}`. When the user clicks, `slack-interactions/handleAeoNext` re-invokes that MCP tool directly with the same workspace context (no LLM roundtrip). Fields required to make those buttons work are marked **[button-critical]** below.

---

## 1. `get_visibility_report` → Pulse card

Renderer: `renderPulseCard`

```jsonc
{
  "overall_score": 74,          // number 0-100 — one of overall_score | overall | score is REQUIRED
  "summary": "Visibility is up on ChatGPT this week…",  // optional mrkdwn, ≤2900 chars
  "engines": [                  // REQUIRED unless overall_score is present; recommended either way
    {
      "name": "ChatGPT",        // string (or `engine`)
      "score": 82,              // 0-100
      "delta": 3.4              // signed number — pt change; renders as ▲/▼
    },
    { "name": "Perplexity", "score": 68, "delta": -1.2 },
    { "name": "Gemini", "score": 71, "delta": 0 }
  ]
}
```

Renders as: header `AEO Pulse — 74%`, optional summary, 2-column engine grid, then buttons **See Rivals** (`get_rival_analysis`) and **Find Gaps** (`get_content_gaps`).

**Empty-state:** returned by the renderer if both `engines` is empty AND `overall_score/overall/score` is missing.

---

## 2. `analyze_topic` → Topic card

Renderer: `renderTopicCard`

```jsonc
{
  "topic": "best AI meeting notes",   // REQUIRED, string  [button-critical]
  "visibility": 42,                    // 0-100 (or `score`)
  "winners": ["Otter.ai", "Fireflies"],// ≤6 competitor names
  "engines_hit": ["ChatGPT", "Perplexity"],
  "summary": "You're cited by ChatGPT but missing from Perplexity's top 5…"
}
```

Buttons emitted: **Why did we drop?** (`analyze_drop_root_cause` w/ topic), **See Proof** (`get_raw_ai_answer` w/ topic+engine=chatgpt), **Content Strategy** (`get_content_gaps` w/ topic). All three require `topic`.

---

## 3. `get_rival_analysis` → Rivals card

Renderer: `renderRivalsCard`

```jsonc
{
  "competitor": "Otter.ai",     // string, headline label (or `rival`); "Competitors" if omitted
  "summary": "Otter dominates ChatGPT citations for meeting-notes queries.",
  "rows": [                      // REQUIRED unless summary present; use `rows` OR `competitors`
    {
      "name": "Otter.ai",       // string (or `competitor`)
      "share_of_voice": 38,     // 0-100 (or `sov` or `score`)
      "delta": 2.1              // signed pt change
    },
    { "name": "Fireflies", "share_of_voice": 24, "delta": -0.8 }
  ]
}
```

Buttons: **Their sources** (`get_raw_ai_answer` w/ topic=competitor, engine=perplexity), **Content Gap vs them** (`get_content_gaps` w/ competitor).

---

## 4. `analyze_drop_root_cause` → Why card

Renderer: `renderWhyCard`

```jsonc
{
  "topic": "best AI meeting notes",   // optional but recommended [button-critical]
  "root_cause": "Perplexity started citing G2 reviews you're missing from.", // or `cause` or `summary`
  "factors": [                         // optional, ≤8 rendered
    {
      "name": "Missing from G2 reviews",  // (or `factor`)
      "impact": 42,                        // 0-100 (or `weight`)
      "detail": "You're not on G2's top-10 AI transcription list."  // (or `note`), ≤220 chars
    }
  ]
}
```

Buttons: **Fix with content brief** (`get_content_gaps` w/ topic), **Alert if worsens** (`get_visibility_report` w/ alert=true+topic).

Renderer returns null (and falls back to markdown) if BOTH `root_cause` and `factors` are missing.

---

## 5. `get_content_gaps` → Gaps card

Renderer: `renderGapsCard`

```jsonc
{
  "topic": "meeting notes AI",        // optional context for header  [button-critical for save action]
  "summary": "6 high-priority gaps you can close this week.",
  "gaps": [                            // REQUIRED; may be `opportunities` instead
    {
      "title": "How to summarize Zoom meetings with AI",  // (or `query` or `topic`)  [button-critical]
      "priority": 87,                                     // 0-100 (or `score`)
      "volume": 2400,                                     // any string/number (or `searches`)
      "summary": "Zero coverage across all 3 engines; competitors also miss." // (or `rationale`), ≤240 chars
    }
  ]
}
```

Each gap renders as a section with an inline **Brief** accessory button (`get_raw_ai_answer` w/ topic=gap.title, engine=chatgpt). ≤6 gaps rendered.

Footer button: **Save to Workstream** (`get_content_gaps` w/ topic+save=true).

Renderer returns null if `gaps` (and `opportunities`) are empty.

---

## 6. `get_raw_ai_answer` → Proof card

Renderer: `renderProofCard`

```jsonc
{
  "topic": "best AI meeting notes",   // recommended [button-critical]
  "engine": "chatgpt",                 // recommended — one of chatgpt|perplexity|gemini|claude
  "answer": "The best AI meeting notes tool in 2025 is Otter.ai, followed by…", // REQUIRED (or `raw`)
  "sources": [                         // optional, ≤6 rendered; may be `citations`
    { "url": "https://otter.ai", "title": "Otter.ai — AI Meeting Notes" },
    "https://fireflies.ai"             // bare string URL also accepted
  ]
}
```

Renderer chunks long `answer` text into ≤4 quote-style blocks. Emits a "Re-run on {other engine}" button that flips chatgpt↔perplexity.

Renderer returns null if `answer` is empty/missing.

---

## 7. Long-running scans — the `trigger_aeo_analysis` contract

`trigger_aeo_analysis` is invoked by the **"Run a Live Scan"** button on empty-state cards. The Slack interactivity path has a hard **90 s ceiling** (`callMcpTool(session, tool, args, 90_000)` in `slack-interactions/handleAeoNext`). If the backend can't return within that window:

- On MCP timeout (`mcp_call_timeout | mcp_timeout | mcp_stream_closed`) the handler now enqueues a row in `public.aeo_pending_jobs` and posts an "I've queued this in the background" message. `aeo-job-runner` (cron) drains the queue with a **240 s** budget and posts the final card into the same thread.
- If the backend prefers to return fast, respond within ~30 s with either:
  - a partial payload that renders as one of the six cards above, OR
  - `{"status":"queued","job_id":"…"}` — this currently renders as the friendly empty-state card; backend can then post the completed result via `chat.postMessage` when ready.

---

## 8. Testing checklist for backend changes

Before shipping a payload shape change:

1. Post the raw JSON string through `renderAeoJsonCard("mcp__grayn_aeo__<tool>", jsonString)` in a Deno test. `null` means the premium card won't render — check required fields above.
2. Confirm every `[button-critical]` field is present, otherwise follow-up buttons will fire with empty args and the next tool call will get no context.
3. Send a deliberate `{"error":"…"}` payload for at least one negative test to confirm the empty-state card renders with recovery buttons.
4. If the tool can exceed 60 s of processing, confirm the fallback path (`aeo_pending_jobs`) picks it up — check `supabase functions logs aeo-job-runner`.

## Notes on the 90s timeout ceiling

Grounded in the current code (`slack-interactions/handleAeoNext` uses `openMcp(url, 60_000) + callMcpTool(..., 90_000)`; main mention path in `_lib/mcp-tools.ts` uses the same 90s budget before enqueueing to `aeo_pending_jobs`):

`trigger_aeo_analysis` is the only tool that structurally requires long work — it's a live scan across engines. The other five (`get_visibility_report`, `analyze_topic`, `get_rival_analysis`, `analyze_drop_root_cause`, `get_content_gaps`, `get_raw_ai_answer`) are all cache/DB reads over pre-computed tracking data and should return in <5s. If any of them start hitting the 90s ceiling, it's a backend regression (cold cache, missing index, or accidentally triggering a scan inline), not an expected shape.

Two known risk cases worth flagging to the backend team:

1. `get_raw_ai_answer` with a topic that has no cached answer — if the backend falls through to a live model call to fetch it, that can blow past 90s. Recommend: return the empty-state error shape and let the user click "Run a Live Scan" instead.
2. `get_content_gaps` on a brand-new topic — same pattern; if it triggers gap computation on demand rather than reading pre-computed gaps, it's slow.

Both `slack-interactions` (button clicks) and `slack-events-handler` (mentions) now have the `aeo_pending_jobs` fallback, so any tool that times out gets picked up by `aeo-job-runner` on its 240s budget — but the backend team should still treat >90s on the five read-tools as a bug, not a feature.
