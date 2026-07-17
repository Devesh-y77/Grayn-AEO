# Grayn — Architecture Deep-Dive (July 2026)

Companion to `docs/ARCHITECTURE_2026.md`. Every claim is anchored to code with
`file:line` refs so the doc stays verifiable as the system evolves.

> **Scope.** How the Slack bot, Supabase backend, MCP layer, and adjacent
> modules (Save-to-Drive, Competitor Watch, CLM, Meta/Google/GA4/GSC, RAG)
> actually run in production today.

---

## 0. Deployment topology (one page)

```text
                        ┌───────────────────────────────────────────┐
  Slack workspace ─────►│  Events API      → slack-events-handler   │
                        │  Interactivity   → slack-interactions     │
                        │  Slash commands  → slack-slash-command    │
                        │  OAuth install   → slack-oauth-callback   │
                        └──────────────┬────────────────────────────┘
                                       │  service-role
                                       ▼
                        ┌───────────────────────────────────────────┐
                        │            Supabase Postgres              │
                        │  slack_workspaces / _connections /        │
                        │  _conversation_log / _flow_context        │
                        │  mcp_servers / mcp_tool_catalog_cache     │
                        │  aeo_pending_jobs / aeo_content_gaps      │
                        │  clm_enabled_workspaces / clm_messages    │
                        │  competitor_watch_workflows/_runs         │
                        │  generated_files (storage: slack-*)       │
                        │  meta_/google_/apple_/revenuecat_/gsc_ *  │
                        │  rag_documents (pgvector)                 │
                        └──────────────┬────────────────────────────┘
                                       │
       ┌────────────────┬──────────────┼────────────────┬─────────────────┐
       ▼                ▼              ▼                ▼                 ▼
  aeo-job-runner   competitor-*    clm-* (7 fns)   Meta/Google/     drive-upload-binary
  (pg_cron 1m)     watch-*         + clm-trigger   GA4/GSC/Apple/    (Google Drive REST)
                                                    RevenueCat
       │                │              │                │                 │
       ▼                ▼              ▼                ▼                 ▼
  MCP SSE          ScrapeCreators  Slack Web +      Provider REST     Google Drive
  (grayn-aeo)      + Meta Ad Lib   Resend/SES       (native fetch)    (multipart)
```

**Rule of thumb.** Only the six AEO tools go through the MCP protocol
(`_shared/mcp-client.ts` → the `grayn-aeo` row in `mcp_servers`). Every other
external system — Meta, Google Ads, GA4, GSC, Apple Search Ads, RevenueCat,
Slack itself, Google Drive, ScrapeCreators, Anthropic, Voyage — is a direct
`fetch()` from its own edge function or shared helper.

---

## 1. Core Event Architecture & Routing

### 1.1 The two Slack entry points

Slack has two Request URLs pointing at two different Supabase functions:

| Slack surface | Function | Purpose |
|---|---|---|
| Event Subscriptions | `slack-events-handler` | All `event_callback` traffic — DMs, `@mention`, thread replies, `app_home_opened`. Signature-verified with `SLACK_SIGNING_SECRET`. |
| Interactivity & Shortcuts | `slack-interactions` | Every `block_actions` payload — Save-to-Drive, Quick Actions, `flow_prompt`/`flow_task`, `aeo_next`. Separate signing, separate signature verifier. |
| Slash commands | `slack-slash-command`, `ga4-slash-command`, `googleads-slash-command` | `/aeo`, `/ga4`, `/googleads` shortcuts. |
| OAuth install | `slack-oauth-init` / `slack-oauth-callback` | Standard Slack v2 OAuth; persists into `slack_workspaces`. |

The two handlers deliberately do **not** import each other. `slack-interactions`
re-uses the events pipeline for LLM-driven buttons by *replaying a signed
synthetic `event_callback`* against `slack-events-handler`
(`slack-interactions/index.ts:310–375`, `replayAsSlackMessage`). This avoids
extracting the 12.7k-line events handler and keeps DM/LLM logic in one place.

### 1.2 Request lifecycle inside `slack-events-handler`

`supabase/functions/slack-events-handler/index.ts:8038` is the single
`serve()` entrypoint. Everything below happens **synchronously inside that
request** — the handler does not ack early with an ephemeral placeholder and
then run in the background. Instead it relies on Slack's retry-suppression
header (see 1.4).

Ordered steps:

1. **Signature verify** — HMAC-SHA256 over `v0:{timestamp}:{body}` using
   `SLACK_SIGNING_SECRET` (`index.ts:8086`). 5-minute freshness window in
   `slack-utils.ts`.
2. **URL verification** — replies to the `type=url_verification` challenge
   (`index.ts:8058`).
3. **`block_actions` fork** — form-encoded interactivity payloads
   accidentally routed here are handled in-place
   (`index.ts:8099` onwards). New interactivity should be sent to
   `slack-interactions`; this branch is legacy.
4. **`event_callback` classify** — `classifySlackEvent(event)`
   distinguishes app-mention, DM, thread-reply, group-DM, channel message
   (`_lib/handlers/event-dispatch.ts`; call at `index.ts:10098`).
   `subtype: "thread_broadcast"` is treated as a regular message so
   @Grayn replies to broadcasts too.
5. **Ignore lists** — `app_mention` events are dropped on purpose because
   Slack fires *both* `app_mention` and `message` for every mention
   (`index.ts:10094`). Only `message` continues.
6. **Dedupe** — see 1.3.
7. **Workspace lookup** — `slack_workspaces` row by `team_id` gives the bot
   token (`index.ts:10130`).
8. **Mention gate** — channel messages and group DMs require the bot to be
   explicitly `@`-mentioned. Thread replies require either an
   @mention or that the bot already participated in that thread
   (`index.ts:10158–10188`).
9. **Message extraction & thread history** — pulls up to N prior turns from
   the thread (`fetchThreadHistory`, called at `index.ts:10412`).
10. **Prompt selection** — see 1.5.
11. **Memory injection** — Grayn Memory blob appended
    (`_lib/memory/loader.ts`, invoked at `index.ts:10432`).
12. **Tool loop** — Anthropic tool-use loop; on each `tool_use` the handler
    either dispatches an MCP tool (`isMcpToolCall` → `dispatchMcpToolCall`)
    or runs a native tool via the local registry
    (`index.ts:10758` for the main path; equivalent blocks at 8287/8832/9510
    for followup/report/creative paths).
13. **Response render + flow buttons** — the tool result is optionally
    turned into Block Kit blocks via `formatAeoMcpResult`
    (`_shared/aeo-format.ts:947`) or a native `buildXBlocks` helper, then
    posted through `sendWithFlowButtons`
    (`_shared/flow-buttons.ts:277`) which appends guided next-step buttons
    or splits them into a follow-up message when the base card is > 12
    blocks (Slack's "Show more" fold threshold).
14. **Return 200** — only after the message is posted.

### 1.3 Deduplication strategy

There are **three** dedupe layers, each addressing a different failure mode.

**Layer A — Slack retry header (`index.ts:8074–8078`).**
If Slack didn't get a 200 within 3s it retries with
`x-slack-retry-num: 1..3`. The handler **short-circuits every retry to
`200 OK` without doing any work**. This is the primary reason we can afford
to run the whole tool loop synchronously: as long as we eventually return 200
once, Slack stops retrying, and we never risk re-executing the same tool.

**Layer B — In-memory event cache
(`_lib/dedup.ts`).**
A process-local `Map<eventId, ts>` (`processedEvents`) with 60 s TTL keyed on
`event.client_msg_id || event.ts || payload.event_id`
(`index.ts:10116–10125`). This catches the case where Slack multiplies events
across two edge isolates (both isolates cold-start, both process the same
event) — whichever isolate wins the race sets the key; the other one bails.
There is a matching cache for interactivity (`processedInteractions`,
45 s TTL) and a per-family concurrency lock (`inFlightInteractionLocks`,
120 s TTL).

**Layer C — Cross-event redundancy filter.**
`app_mention` is entirely dropped (`index.ts:10094`), because Slack sends
both `app_mention` and `message` for every `@Grayn`. Bot-self-replies,
`bot_message` subtype, and messages with no `user` are also dropped
(`index.ts:10111`, `10143`).

> **Why not an ephemeral "thinking…" ack?** Because Layer A already solves
> the 3-second window: Slack's own retry is what would otherwise cause
> duplicates, and we neutralise it. We do use an ephemeral ack in
> `slack-interactions` (see 1.6) because button clicks are single-shot and
> the user benefits from seeing "⏳ Saving…" immediately.

### 1.4 The 3-second window in practice

| Function | Ack strategy | Reason |
|---|---|---|
| `slack-events-handler` | Suppress `x-slack-retry-num`, run the whole tool loop synchronously, return 200 when the reply is posted. | Simpler, no isolate-suspension surprises; message ordering is preserved. |
| `slack-interactions` | Ack `200` immediately at `index.ts:784`; real work runs in `EdgeRuntime.waitUntil()` (`index.ts:738/750/758/766/774`). | Interactivity strictly requires <3s ack; work is bounded and fire-and-forget. |
| `aeo-job-runner` | HTTP 200 after draining ≤5 jobs — no Slack ack required (it's cron-invoked). | Runs in the background. |
| `competitor-watch-dispatcher` | Same — cron only. | Same. |

### 1.5 Prompt routing: compact vs full

Two prompts live at `_lib/prompts/system-full.ts` (700 lines) and
`_lib/prompts/system-compact.ts` (121 lines). Selection is deterministic
(`index.ts:10419–10422`):

```ts
let systemPrompt = threadHistory.length > 0
  ? buildCompactSystemPrompt(...)
  : buildSystemPrompt(...);
```

- **Full** — first turn of a conversation. Includes the full metrics
  glossary, GSC/organic routing rules, month/date parsing rules, the AEO
  intent instructions, GTM routing, and per-platform strict rules
  (Google Ads not-connected verbatim reply, CPI recompute guard, etc.).
- **Compact** — every follow-up in a thread. Assumes the model already saw
  the full prompt earlier in the thread; trims to a few hundred tokens of
  glossary + Slack-formatting rules. Anthropic prompt caching is applied on
  the system block so we don't pay for the full prompt each turn.

Additionally, an **AEO intent nudge** (`index.ts:159–172`, `aeoNudge()`) is
*regex-appended* to the system prompt whenever the user's message matches
AEO phrasing. It's a soft override: it does not touch `tool_choice`, but it
tells Claude it MUST call one of the `mcp__grayn_aeo__*` tools this turn.
This is the deterministic backstop that keeps AEO questions from being
answered from parametric knowledge.

### 1.6 Sync MCP vs async `aeo-job-runner`

Every MCP call goes through the same in-process path first
(`_lib/mcp-tools.ts:246 dispatchMcpToolCall`):

```ts
const session = await openMcp(hit.server.url);      // SSE handshake ~25s cap
const { text, raw } = await callMcpTool(session, hit.toolName, mergedArgs);
```

If the call throws with `mcp_call_timeout | mcp_timeout | mcp_stream_closed`
the handler wraps it in a friendly "⏳ Still running…" reply *and* enqueues a
row into `aeo_pending_jobs` (`_lib/mcp-tools.ts:371 enqueueAeoJob`, called
from `index.ts:10765`). A pg_cron entry hits `aeo-job-runner` every minute;
that function re-opens the MCP session with a **4-minute** budget
(`aeo-job-runner/index.ts:117`), formats the result with `formatAeoMcpResult`,
and posts it back to the original `channel + thread_ts`.

Decision matrix:

| Situation | Path |
|---|---|
| MCP tool returns in <25s | Sync dispatch, reply in-line with flow buttons. |
| MCP tool times out mid-call | Sync fallback message + enqueue → job runner replies later. |
| Long AEO scan initiated by a `aeo_next` button | `slack-interactions handleAeoNext` runs the MCP call inside `waitUntil` with a 90s cap; on timeout the user is told to expect a background result. |
| Non-MCP tool (Meta/Google/GA4/etc.) | Native fetch inside the tool loop; timeouts surface as a friendly "unavailable" reply. |

`aeo_pending_jobs` also tracks `attempts`, `started_at`, `completed_at`,
`last_error`, and `result_text` so failed jobs are retried up to 3 times
before Grayn posts a give-up message (`aeo-job-runner/index.ts:156–175`).

---

## 2. State Management & Database

### 2.1 Slack surface tables

| Table | Purpose | Written by | Read by |
|---|---|---|---|
| `slack_workspaces` | One row per Slack team install. Holds `team_id`, `access_token`, `bot_user_id`, `is_active`. | `slack-oauth-callback` | Every Slack function on every request. |
| `slack_workspace_connections` | Joins a `slack_workspaces.id` to a Grayn `workspace_id`. Multiple app workspaces can share one Slack install. | Dashboard "Connect Slack" flow | `resolveWorkspaceId` in `slack-interactions/index.ts:260`; workspace repo in the events handler. |
| `slack_channels` | Cache of `conversations.list` for the channel picker in the dashboard. | `slack-list-channels` | Dashboard UI. |
| `slack_user_mappings` | Maps `slack_user_id` → app user. | `slack-link-user` + auth flows | Attribution/audit. |
| `slack_conversation_log` | Full turn-by-turn transcript with model/token/cost metadata. | `slack-events-handler` at end of each turn | Analytics, admin, debug. |
| `slack_flow_context` | Ephemeral state for `flow_prompt`/`flow_task` buttons. See 2.3. | Events handler (`writeFlowContext`) | `slack-interactions` (`readFlowContext`). |
| `slack_flow_task` context (transient) | Not a table — payload passed function-to-function via HTTP. | — | — |

### 2.2 MCP / AEO tables

| Table | Role |
|---|---|
| `mcp_servers(id, workspace_id, name, url, enabled, ...)` | Registry of MCP endpoints. `workspace_id IS NULL` = global (currently only `grayn-aeo`). Rows are selected in `_lib/mcp-tools.ts:66 fetchEnabledServers` — global + this workspace's rows. |
| `mcp_tool_catalog_cache(server_id, tools jsonb, fetched_at)` | Cold-start warmup for tool schemas. Populated after every successful `tools/list` call (`_lib/mcp-tools.ts:115 persistCatalog`). Read at 174–194 as a fallback when the live SSE fetch fails, so Claude still sees the tools during a partial outage. |
| `aeo_pending_jobs` | Async work queue for MCP calls that exceeded the sync window. Columns: `workspace_id`, `slack_team_id`, `slack_channel`, `slack_thread_ts`, `bot_token`, `tool_name`, `tool_args jsonb`, `status ∈ {pending, running, completed, failed}`, `attempts`, `last_error`, `result_text`, `created_at/started_at/completed_at`. |
| `aeo_content_gaps` | Persisted content-gap opportunities (produced by AEO tools) — used by "Save to Workstream" and by CLM's gap-count metric. |

### 2.3 `slack_flow_context` — how state survives a button click

Slack `block_actions` payloads carry at most 2000 chars in `value`, and the
message blocks themselves are immutable across sessions. To carry structured
context (topic, competitor domain, timeframe, tool call args) from one turn
to the next we persist a row and put only its UUID into the button's `value`.

**Write** (`_shared/flow-buttons.ts:189 writeFlowContext`, called at
`index.ts:10786, 8314, 8663, 8859, 9242, 9537, 12657`):

```ts
await client.from("slack_flow_context").insert({
  workspace_id, slack_team_id, slack_channel, slack_thread_ts,
  intent,              // classifyIntent(toolName, text)
  payload,             // { tool, args, brand_name?, competitor?, topic?, ... }
}).select("id").single();
```

**Emit** (`buildFlowBlocks` in the same file). The button value becomes
`"<flow_key>:<uuid>"`, and `action_id` starts with `flow_prompt_` or
`flow_task_` so `slack-interactions` can route by prefix
(`slack-interactions/index.ts:756/764`).

**Read** (`_shared/flow-buttons.ts:222 readFlowContext`, used in
`handleFlowPrompt` and `handleFlowTask`). The payload's `competitor`,
`brand_name`, `topic` etc. seed the canonical prompt string that gets
replayed into `slack-events-handler`.

For the AEO `aeo_next` cards we take a different route: `renderAeoJsonCard`
embeds the *full tool call* into the button value as JSON —
`{"t":"analyze_topic","a":{"topic":"..."}}` — because the args are small and
bounded. `handleAeoNext` calls the MCP tool directly with those args and
skips the LLM (`slack-interactions/index.ts:564–686`). That saves a round-trip
for pure "drill-down" clicks.

### 2.4 CLM tables

| Table | Role |
|---|---|
| `clm_enabled_workspaces(workspace_id, enabled_at, note)` | Fail-closed allowlist. `_shared/clm/lib.ts:60 isWorkspaceEnabled` is called by every CLM sender before it does anything. Env var `CLM_ALLOWLIST_WORKSPACE_IDS` is additive. |
| `clm_messages` | Per-`(workspace_id, message_key, ...)` send-log used by `clm-trigger` to dedupe. |
| `clm_dm_fallback_log` | Records when a Slack DM couldn't be delivered (user not in workspace, DM disabled) so we can fall back to email. |

### 2.5 Other core tables invoked by the Slack pipeline

- **`generated_files`** — one row per PDF/DOCX/XLSX/CSV/TXT the bot renders,
  with `storage_path` in the `slack-generated-files` bucket and
  `drive_file_id/drive_web_view_link/saved_to_drive_at` populated after the
  Save-to-Drive click succeeds.
- **`competitor_watch_workflows`** — user-configured watch rules
  (`advertisers jsonb`, `detection jsonb`, `insights jsonb`, `schedule_cron`,
  `timezone`, `slack_channel_id`, `email_recipients[]`, `last_status`,
  `last_error`, `last_run_at`, `next_run_at`, `slack_workspace_id`).
- **`competitor_watch_runs`** — audit trail of each `competitor-watch-run`
  invocation.
- **Meta / Google / Apple / RevenueCat / GSC / GA4 tables** — one per
  platform integration with `*_ad_accounts`, `*_permissions`, `*_campaigns`,
  `*_insights_daily`, etc. Populated by the OAuth/fetcher functions and
  queried by the Slack tool handlers.
- **`rag_documents`** — pgvector store for Voyage embeddings, queried by
  `rag-search`.

### 2.6 How thread context becomes a follow-up prompt

1. `fetchThreadHistory` (`index.ts:10412`) hits Slack's
   `conversations.replies` for prior messages between the user and the bot.
2. That history is passed to Claude as `messages[]`.
3. The **compact** system prompt is used because `threadHistory.length > 0`.
4. If the previous turn wrote a `slack_flow_context` row, the button that
   triggered this follow-up carried its UUID → `readFlowContext` merges the
   remembered `brand_name/competitor/topic` into the canonical replay prompt
   *before* it hits the LLM.
5. AEO context (workspace `url`, `client_name`, `domain`, `target_brand`,
   `workspace_ref`) is auto-injected into every MCP tool call by
   `_lib/mcp-tools.ts:263–322` regardless of what Claude sent — the model
   never has to remember it.

---

## 3. Modules Beyond AEO

### 3.1 Save-to-Drive

**Trigger:** any generated file is exported through
`_shared/upload-generated-file.ts` → row in `generated_files` → the reply
includes the button rendered by `_shared/save-to-drive-button.ts:19`
(`action_id: "save_to_drive"`, `value: <file_id>`).

**Flow (`slack-interactions/index.ts:148 handleSaveToDrive`):**
1. Immediate in-place ack via Slack's `response_url` — the button block is
   replaced with a "⏳ Saving to Google Drive…" context block.
2. `uploadBinaryToDrive(fileId, supabase)` in `_shared/drive-upload.ts`:
   - Look up the workspace's Google account
     (`google_ad_accounts` most-recent active row).
   - Refresh the access token if expired, using `GOOGLE_ADS_CLIENT_ID/SECRET`.
   - Download the binary from the `slack-generated-files` storage bucket.
   - `POST` to `https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart`
     with the multipart boundary the helper builds at
     `_shared/drive-upload.ts:72–80`.
3. Success → the button block is replaced with a `✅ Saved <name> → Open in Drive` context block, and `generated_files.drive_file_id/link/saved_to_drive_at` are updated.
4. Failure → friendly error message keyed on `NO_GOOGLE_CONNECTION` or
   `MISSING_DRIVE_SCOPE` with a "Reconnect Google" link and a "🔄 Try Again"
   retry button (`slack-interactions/index.ts:214–255`).

**Ownership:** workspace-level (shared destination), never per-Slack-user.

### 3.2 Competitor Watch

**Table:** `competitor_watch_workflows` (see 2.5).

**Two entry points:**
- Dashboard: `src/components/workflows/*` writes rows directly.
- Slack: `_lib/handlers/competitor-watch.ts` handles Grayn-native creation
  from a `@mention` request. Rows created in Slack are visible in the
  dashboard's "Workflows" tab because both paths write the same table.

**Runtime:**
```text
pg_cron (1 min) ─► competitor-watch-dispatcher ─► competitor-watch-run
                        │ cronMatches(cron, tz)      │ (async via
                        │ (see index.ts:9–43)        │  EdgeRuntime.waitUntil)
                        ▼                            ▼
           filters is_active rows whose        ScrapeCreators + Meta Ad Library
           schedule_cron matches now in tz     + Google Ads Transparency
                                                + Whisper/HCTI for transcripts
                                                & image cards
                                                ▼
                                         chat.postMessage into the
                                         workflow's slack_channel_id
```

`last_status`/`last_error` are updated after every run so the dashboard
shows the workflow's health. Long runs are protected by
`EdgeRuntime.waitUntil` so the HTTP response returns instantly, avoiding
HTTP timeouts on the dispatcher.

**External APIs:** ScrapeCreators (bearer key `SCRAPECREATORS_API_KEY`),
Meta Ad Library (via `meta-search-ad-library`), Google Ads Transparency
(via `scrapecreators-google-search-ads`), HCTI for chart PNGs.
**Not MCP** — every call is a direct fetch.

### 3.3 CLM v2 (Customer Lifecycle Management)

**Orchestrator:** `clm-trigger` (allowlist-gated by
`clm_enabled_workspaces`). Dry-run mode is exercised from the Admin panel.

**Fan-out:** `clm-trigger` dispatches into topic-specific senders:

| Function | Trigger | Channel |
|---|---|---|
| `clm-onboarding-slack` | Day-0..N onboarding drip | Slack DM |
| `clm-recurring-slack` | Weekly/monthly summaries | Slack DM/channel |
| `clm-atrisk-slack` | Churn signals | Slack DM |
| `clm-email-sequences` | Cross-channel email drips | Resend |
| `clm-reengage-email` | 30-day inactive | Resend |
| `clm-alert-subscriber` | Alert config → subscriber | Slack/email |
| `clm-state-updater` | Advances a workspace's lifecycle stage | DB write |

**Shared libs:** `_shared/clm/lib.ts` (allowlist + admin client),
`_shared/clm/data.ts` (enrichment queries), `_shared/clm/messages.ts` (copy
for all 20 message keys), `_shared/clm/shell.ts` (HTML shell for email).

**Not MCP.** No external agent involvement; everything is Slack Web API +
Resend.

### 3.4 Meta / Google Ads / GA4 / GSC / Apple / RevenueCat

All follow the same three-function pattern:

```text
*-oauth-init    ─┐
*-oauth-callback ├─► rows in <platform>_ad_accounts (+ *_permissions)
*-connect-account┘
*-fetch-*       ── called from the Slack tool loop's runTool() ──►
                   returns normalized rows the LLM turns into a reply
```

Concrete examples:
- **Meta:** `meta-oauth-init`, `meta-oauth-callback`, `meta-connect-account`,
  `meta-connect-bm`; fetchers `meta-fetch-ads`, `meta-fetch-adsets`,
  `meta-fetch-campaigns`, `meta-fetch-insights`, `meta-fetch-demographics`;
  writers `meta-write-api`, `meta-diagnose-write-access`,
  `meta-token-sweeper` (cron), `meta-search-ad-library`
  (competitor watch feeder).
- **Google Ads:** `google-oauth-init/callback/connect-account` and a fetcher
  per resource (`google-fetch-campaigns`, `-conversion-actions`,
  `-asset-groups`, `-keywords`, `-negatives`, `-extensions`,
  `-experiments`, `-demographics`, `-insights`, `-billing`). Writer:
  `google-write-api`. Auth helper: `_shared/google-ads-auth.ts`.
- **GA4:** `google-analytics-oauth-init/callback`,
  `google-analytics-connect-account`, `google-analytics-fetch-data`,
  `google-analytics-fetch-pages`.
- **GSC:** `gsc-oauth-init/callback`, `gsc-connect-property`,
  `gsc-fetch-data`.
- **GTM:** `gtm-oauth-init/callback`, `gtm-connect-account`,
  `gtm-fetch-data`.
- **Apple Search Ads:** `apple-connect-account` (JWT via
  `_shared/apple-token.ts`), `apple-fetch-insights`.
- **RevenueCat:** `revenuecat-oauth-init/callback`, `revenuecat-connect`,
  `revenuecat-fetch-metrics`.

**None of these are MCP.** The AI SDK sees them as static tools registered in
`_lib/ai-tools.ts` (`AI_TOOLS`), and `withMcpTools()`
(`_lib/mcp-tools.ts:221`) concatenates the MCP-discovered tools on top.
`runTool()` in `_lib/dispatch/run-tool.ts` dispatches native tools; MCP tools
are caught by `isMcpToolCall` earlier in the tool loop.

### 3.5 RAG

`rag-ingest` chunks (`_shared/rag-chunk.ts`) and enqueues via
`_shared/rag-enqueue.ts`; `embed-worker` pulls the queue and calls
Voyage (`_shared/voyage.ts`) to write vectors into `rag_documents`.
`rag-search` runs `rag_match_documents` (SQL function) for the Slack tool
loop when the model calls the `rag_search` tool. `rag-backfill` +
`rag-backfill-trigger` catch up historical content.

### 3.6 What actually uses MCP

**Just the six AEO tools.** `mcp_servers` currently holds one enabled
global row named `grayn-aeo` pointing at the Python backend
(`https://api.grayn.ai/mcp`) authenticated with `MCP_API_KEY`
(`_shared/mcp-client.ts:51 mcpAuthHeaders`). Everything else is a native
edge function.

---

## 4. Error Handling & Edge Functions

### 4.1 Deployment structure

- Every directory directly under `supabase/functions/*` (except `_shared/`)
  is an independently deployed Deno function.
- `_shared/` and each function's `_lib/` are **not deployed** — they're
  imported at bundle time. This is why `slack-interactions` and
  `slack-events-handler` both import `_shared/mcp-client.ts` instead of
  calling each other over HTTP.
- `verify_jwt` is off for public webhooks (Slack, OAuth callbacks,
  Drive/Meta callbacks). Signatures are validated in code.
- Secrets used (from `supabase/config.toml` / dashboard):
  `ANTHROPIC_API_KEY`, `SLACK_SIGNING_SECRET`, `SLACK_API_KEY`,
  `SLACK_CLIENT_ID/SECRET`, `MCP_API_KEY`, `META_APP_ID/SECRET`,
  `GOOGLE_ADS_CLIENT_ID/SECRET`, `GOOGLE_ADS_DEVELOPER_TOKEN`,
  `SCRAPECREATORS_API_KEY`, `HCTI_API_KEY`, `VOYAGE_API_KEY`,
  `DATAFORSEO_LOGIN/PASSWORD`, `GRAYN_AEO_API_URL/API_KEY`,
  `ANTHROPIC_ADMIN_API_KEY`.

### 4.2 Timeout budgets (measured, not aspirational)

| Boundary | Budget | Where set |
|---|---|---|
| Slack retry | 3 s | Handled by `x-slack-retry-num` short-circuit (`index.ts:8074`). |
| MCP SSE handshake | 45 s | `openMcp(url, 45_000)` for catalog load (`_lib/mcp-tools.ts:95`). |
| MCP tool call (sync path) | 25 s default | `DEFAULT_TIMEOUT_MS` in `_shared/mcp-client.ts:43`. |
| MCP tool call (`aeo_next` button) | 90 s | `callMcpTool(session, tool, args, 90_000)` (`slack-interactions/index.ts:643`). |
| MCP tool call (background runner) | 240 s | `aeo-job-runner/index.ts:117`. |
| Anthropic call | Handled by `_lib/ai.ts` with retry + exponential backoff on 429/5xx (`callClaude`). Overload debounce via `lastClaudeOverloadTime`. |
| Provider fetches (Meta/Google/etc.) | Default `fetch` (no explicit timeout); surfaced as friendly "unavailable" reply on throw. |
| Long AEO scan | Enqueued into `aeo_pending_jobs`; job runner retries up to 3 times before giving up. |

### 4.3 Error surfacing

- **MCP-level tool errors** (`raw.isError === true`) are normalized into a
  JSON error envelope `{"error": "..."}` in
  `_lib/mcp-tools.ts:327–335`. `renderAeoJsonCard` in `_shared/aeo-format.ts`
  detects the key and renders `renderAeoEmptyStateCard`
  (`_shared/aeo-format.ts:1424`) with recovery actions like
  "🔄 Run a Live Scan" so the user never sees a raw `Error:` string.
- **MCP transport timeouts** (`mcp_call_timeout`, `mcp_stream_closed`,
  `mcp_timeout`) are matched by regex in both `dispatchMcpToolCall`
  (`_lib/mcp-tools.ts:351`) and `handleAeoNext`
  (`slack-interactions/index.ts:675`) — the user gets a
  "⏳ Still running…" message and the job is retried in the background.
- **Slack `invalid_blocks`**: `sendSlackMessage` +
  `sendWithFlowButtons` cap blocks at 50 and split long cards into a card
  + a follow-up buttons message so the report itself is never folded
  under Slack's "Show more" cut (`_shared/flow-buttons.ts:262–297`).
- **Anthropic overload/5xx**: `TRANSIENT_AI_STATUS_CODES` + `sleep` +
  `calculateBackoffMs` retry loop in `_lib/ai.ts`; a workspace-wide
  `lastClaudeOverloadTime` prevents thundering-herd retries.
- **Uncaught throw in the events handler**: outer `try/catch` at
  `index.ts:8050` posts a user-facing "something went wrong" Slack message
  when possible, using `outerSupabaseUrl`/`outerServiceRoleKey`.

### 4.4 CI/dev harness

- `_lib/*_test.ts` files exercise dedup, ai, period parsing, coerce-args,
  chart-theme, report-blocks, snapshot regressions, event-dispatch, and an
  integration test. `deno test` runs them.
- `__snapshots__/` holds golden Block Kit output so we catch accidental
  regressions in Slack formatting.

---

## 5. Sequence diagrams

### 5.1 `@Grayn` question

```text
Slack ── event_callback ──► slack-events-handler:8038
                             │  1. verify signature (v0 HMAC)
                             │  2. drop if x-slack-retry-num set
                             │  3. classify + dedupe (processedEvents)
                             │  4. resolve workspace + bot token
                             │  5. mention/thread gates
                             │  6. fetchThreadHistory (if thread reply)
                             │  7. buildSystemPrompt or buildCompactSystemPrompt
                             │  8. + aeoNudge(userQuery) if AEO intent
                             │  9. + Grayn Memory
                             │ 10. Claude tool-use loop
                             │       ├─ mcp__grayn_aeo__*  ─► dispatchMcpToolCall
                             │       │                        (SSE, 25s cap)
                             │       │      timeout ─► enqueueAeoJob
                             │       └─ native tool        ─► runTool()
                             │ 11. formatAeoMcpResult / buildXBlocks
                             │ 12. writeFlowContext + sendWithFlowButtons
                             │ 13. chat.postMessage
                             └── 200 OK
```

### 5.2 Button click (`flow_prompt`)

```text
Slack ── block_actions ──► slack-interactions:690
                            │  verify sig, ack 200 immediately
                            │  EdgeRuntime.waitUntil(handleFlowPrompt)
                            │     │
                            │     ▼
                            │   parseFlowValue → { key, contextId }
                            │   readFlowContext(contextId) → { brand, competitor }
                            │   promptForFlowKey(key, ctx)  → canonical text
                            │   postSlackMessage("> <canonical prompt>")
                            │   replayAsSlackMessage → signed synthetic event
                            │                          → slack-events-handler
                            │                          (full pipeline 5.1)
                            └── 200 OK (already sent)
```

### 5.3 Button click (`aeo_next` — direct MCP)

```text
Slack ── block_actions ──► slack-interactions:772
                            │  ack 200, waitUntil(handleAeoNext)
                            │    parse {t, a} from action.value
                            │    lookup mcp_servers WHERE name='grayn-aeo'
                            │    enrich args with brand/url/workspace_ref
                            │    postEphemeral("⏳ Running <tool>…")
                            │    openMcp(url, 60s) → callMcpTool(tool, args, 90s)
                            │    renderAeoJsonCard(namespaced, text)
                            │    chat.postMessage(blocks.slice(0,50))
                            │      timeout ─► "retry in ~1 min" message
                            └── 200 OK
```

### 5.4 Long AEO scan

```text
slack-events-handler
  └─ dispatchMcpToolCall → timeout
        └─ enqueueAeoJob → INSERT aeo_pending_jobs(status='pending')
pg_cron (*/1)  ──► aeo-job-runner
                    │  SELECT * WHERE status='pending' AND created_at < now()-5s LIMIT 5
                    │  for each:
                    │    UPDATE status='running', attempts++
                    │    resolveMcpServer(workspace_id, tool_name)
                    │    openMcp(url, 60s) → callMcpTool(..., 240_000)
                    │    formatAeoMcpResult → chat.postMessage(channel, thread_ts)
                    │    UPDATE status='completed', result_text
                    │    on error: attempts<3 → back to pending; ≥3 → failed + Slack "gave up"
                    └── 200 { processed: N }
```

### 5.5 Save-to-Drive

```text
generated_files INSERT ─► reply blocks include saveToDriveButtonBlock(fileId)
Slack click "📁 Save to Google Drive"
   └─ slack-interactions:736 handleSaveToDrive (via waitUntil)
        ├─ respondViaUrl "⏳ Saving…" (replace_original)
        ├─ uploadBinaryToDrive:
        │    getGoogleToken(workspace) → refresh if expired
        │    download from storage 'slack-generated-files'
        │    POST /upload/drive/v3/files (multipart)
        ├─ UPDATE generated_files.drive_file_id/link/saved_to_drive_at
        └─ respondViaUrl "✅ Saved <name> → Open in Drive" or friendly error + Retry
```

---

## 6. Where to make changes safely

- **Add a new AEO tool:** implement it in the Python MCP backend; it appears
  automatically once catalog TTL expires (5 min) or after
  `mcp_tool_catalog_cache` is refreshed. Add a renderer branch in
  `_shared/aeo-format.ts` if you want a bespoke card.
- **Add a new native tool:** append to `AI_TOOLS` in
  `_lib/ai-tools.ts`, register a handler in `_lib/dispatch/register.ts` (or
  add a case in the legacy chain if not yet migrated).
- **Add a next-step button:** extend `FlowKey` + `INTENT_BUTTONS` in
  `_shared/flow-buttons.ts`, then handle it in `handleFlowPrompt`
  (if it just replays a prompt) or `slack-flow-task` (for native/external
  tasks).
- **Add a new CLM message:** add copy to `_shared/clm/messages.ts`, wire a
  dispatch in `clm-trigger`, and remember it's gated on
  `clm_enabled_workspaces`.
- **Do NOT** move Slack logic out of `slack-events-handler` piecemeal — the
  singleton in-memory dedupe maps (`_lib/dedup.ts`) rely on all writers
  sharing one process. Refactor via `_lib/handlers/` extraction instead.

---

_Last verified against `main` on 2026-07-13. Line numbers cite the file
state at that revision; refactors may shift them, but section names and
function names should still match._
