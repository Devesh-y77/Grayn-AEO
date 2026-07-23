# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is (and isn't)

This repo contains **only two of the three systems** that make up Grayn AEO:

1. `frontend/` — Next.js dashboard (deployed to Vercel, project `grayn-aeo`).
2. `backend/` — FastAPI app (deployed to Railway) that exposes:
   - a REST API under `/v1` (`app/routers/v1.py`), consumed by `frontend/`.
   - an MCP server (`app/mcp_server.py`), consumed by an **external** Slack bot.

The Slack bot itself — event handling, Block Kit rendering, CLM, Meta/Google Ads/GA4/GSC integrations, RAG — lives in a **separate** Supabase Edge Functions project, not in this repo. From this backend's point of view, that whole system is just one MCP client. Do not assume Slack-side code (event handlers, edge functions, Block Kit) is reachable here — the closest thing to its docs is `GRAYN_FRONTEND_ARCHITECTURE.md`, which describes that *other* system, not `frontend/`. That doc says the Slack side only wires up "six AEO tools" — `mcp_server.py` actually registers **ten** (see below); treat the doc as slightly stale rather than assuming four tools are dead code.

`AEO_CARD_CONTRACTS.md` (root) is the binding contract for the MCP tools' JSON output — if you change what any of them returns, the Slack cards on the other side will break silently unless the shape still matches this doc.

## Commands

### Backend (`backend/`)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000        # local dev
uvicorn app.main:app --host 0.0.0.0 --port 8000  # matches Dockerfile/production
```
- No pytest suite exists. Verification scripts (`test_report.py`, `test_auth.py`, `test_gemini.py`, `test_anthropic.py`, etc.) are standalone scripts run directly, e.g. `python test_report.py` — they load `.env` via `python-dotenv` and hit the real Supabase/provider APIs, they are not isolated unit tests.
- `USE_MOCK_PROVIDERS=true` in `.env` swaps all AI provider calls for `mock_provider.py` — use this for local runs without burning API credits.
- Playwright is a runtime dependency (`browser_provider.py`); `playwright install chromium` is required once per environment (already baked into `Dockerfile`).

### Frontend (`frontend/`)
```bash
npm run dev     # next dev
npm run build
npm run lint    # eslint
```
No test script is defined in `package.json`.

### Full stack locally
```bash
docker-compose up
```
Builds both services from their `Dockerfile`s; expects `SUPABASE_URL`, `SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY`, and provider API keys as host env vars.

## Backend architecture

`app/main.py` registers four routers on one FastAPI app: `v1` (public dashboard API), `internal` (admin, gated by `X-Admin-Token`), `public_lp` (public landing-page endpoints), and the MCP `router` from `mcp_server.py`. A `lifespan` hook also starts an `AsyncIOScheduler` job (see "Scheduled tracking" below).

**Auth model** (`app/dependencies.py`): three separate schemes coexist —
- `get_current_workspace` — Bearer key (`gk_<prefix>_<secret>`), SHA-256 hashed and looked up in `api_keys`, used by the dashboard/`v1` routes.
- `require_admin` — static `X-Admin-Token` header, used by `internal` routes.
- `verify_slack_api_key` — Bearer key checked against `GRAYN_AEO_API_KEY`, used for the Lovable/Slack-facing endpoints.

**The tracking pipeline** (the core workflow most features touch):
1. `services/discovery.py` — given a URL, scrapes it and asks an LLM to extract brand name, competitors, and suggested queries. Provider fallback order: `openai → deepseek → groq → gemini` (no anthropic). If every provider fails, it returns generic fallback queries and the scan still proceeds — it does not abort.
2. `services/tracking.py` (`trigger_batch_run` / `run_single_prompt`) — dispatches prompts concurrently to whichever AI providers are configured, per-engine concurrency limited by a semaphore (`{ENGINE}_MAX_CONCURRENCY` env var, default 5), with `tenacity` retry/backoff on transient failures. Runs are grouped by `scan_group_id` when a prompt is fired at one engine multiple times (multi-pass consensus, see below).
3. `services/providers/*` — one adapter per AI engine (`openai_provider.py`, `gemini_provider.py`, `google_ai_provider.py`, `groq_provider.py`, `claude_provider.py`, `deepseek_provider.py`, `grok_provider.py`, `perplexity_provider.py`, `browser_provider.py`, `mock_provider.py`), all implementing the `base.py` interface and returning a uniform `EngineResult`. `get_provider()` picks the implementation based on which `*_available` flag is true in `config.py` (auto-selects on whether the API key env var is set, unless `USE_MOCK_PROVIDERS` is on). `browser_provider.py` is a stub, not a real headless browser — its output can diverge from the consumer web UI it's meant to approximate.
4. `services/judge.py` (`extract_mentions_and_citations`) — a secondary LLM pass over the raw provider response, extracting brand/competitor mentions, sentiment, and cited URLs. Fallback order: `deepseek → groq → anthropic → openai → gemini` — **note this is a different order from discovery.py's**, not an oversight to "fix" without checking why. In mock mode (`USE_MOCK_PROVIDERS=true`) or when all providers fail, it returns an **empty** extraction rather than fabricated data, specifically to avoid polluting the DB with fake mentions.
5. `services/scoring.py` — aggregates judged runs into visibility score / share-of-voice / trends (`build_full_report`, `compute_historical_trend`), resolved per ISO week (`2026-W30` format) via `_resolve_week()`, which picks the most recent week containing at least one `status='complete'` run.
6. `services/consensus.py` — when a prompt×engine is run multiple passes in one `scan_group_id`, confidence is `max(rate, 1 - rate) * 100` where `rate` is the fraction of *successful* (`status='complete'`) passes that mentioned the brand — i.e. 3/3 or 0/3 agreement = 100% confidence, 1.5/3 = 50%. Groups where every pass errored score 0 confidence; groups that are only partially failed are scored from the successful passes only, not penalized for the failures.
7. `services/citations.py`, `services/content_analyzer.py`, `services/insights.py`, `services/brand_normalizer.py` — downstream analysis (citation leaderboards, content gap detection via the same 5-provider fallback as the judge, brand name canonicalization/deduping) built on top of judged run data.

Because live multi-engine scans can exceed the Slack-side 90s timeout, long scans are queued (`aeo_pending_jobs`) rather than run synchronously end-to-end when called via MCP — see `AEO_CARD_CONTRACTS.md` §7–8 before changing anything in `trigger_aeo_analysis`'s latency characteristics. The other MCP tools are expected to be cache/DB reads under 5s; if one starts taking 90s, that's a regression (e.g. `get_raw_ai_answer` or `get_content_gaps` falling through to a live/on-demand LLM call instead of reading pre-computed data), not a new feature.

A weekly cron (`AsyncIOScheduler` job registered in `main.py`'s `lifespan`, Monday 02:00 UTC) re-runs `trigger_batch_run` for every workspace's active prompts against `OPENAI`, `GOOGLE_AI`, and `PERPLEXITY`, in chunks of 5 workspaces with a 60s sleep between chunks to stay under provider rate limits.

### Non-obvious invariants — do not "clean up" without checking these first
- **`chunked_in_fetch` (`services/db_helpers.py`) is mandatory for any `.in_()` query against `aeo_mentions`, `aeo_runs`, or `aeo_citations`.** PostgREST returns HTTP 414 (URI too long) once a `run_ids` list gets large; `chunked_in_fetch` batches the `.in_()` call in chunks of 40. A raw `db.table(...).in_(...)` on these tables works fine in dev with a handful of rows and then breaks in production at scale — don't reintroduce it as a "simplification."
- **`aeo_prompts.prompt_text` must always be written as `.strip().lower()`.** There's a unique constraint on `(workspace_id, prompt_text)`; inserting mixed-case or padded text creates duplicate logical prompts that silently fragment tracking history.
- **`is_target_brand` is not an exact-match flag** — it's `m.is_target_brand OR target_lower in m_lower OR m_lower in target_lower OR m_lower.startswith(target_lower) OR target_lower.startswith(m_lower) OR any alias substring match` (`tracking.py`, around the mention-persistence block). This is intentional so "Netflix" also matches "Netflix Inc." / "Netflix.com" — don't tighten it to `==` expecting it to be a bug fix.
- **`analyze_topic`'s topic match (`mcp_server.py`) is keyword-based, not exact-string**: it splits the topic name into lowercase keywords and requires all of them to appear as substrings in the prompt text. A topic filter that doesn't match this loosely will silently return zero runs rather than erroring.
- **`get_top_citations` deliberately filters out competitor domains** (matched by normalizing competitor `brand_name`s into slugs) before building the leaderboard — an empty-looking citation list may mean "everything cited was a competitor," not "no data."

### Database (Supabase/Postgres)
Core tables: `workspaces` (brand_name, domain, aliases), `api_keys`, `competitors`, `aeo_prompts` (prompt_text, unique per workspace — see above), `aeo_runs` (one row per prompt × engine × pass; `status` ∈ `complete`/`error`/`judge_failed`; `scan_group_id` links multi-pass runs; `iso_week`), `aeo_mentions` (`is_target_brand`, `position`, `sentiment`), `aeo_citations`, `brands` (canonical registry used by `brand_normalizer.py`). Schema/migrations live as loose `.sql` files at the `backend/` root (`schema.sql`, `migrate_multipass.sql`, `migration_citations.sql`, `migration_mentions_raw.sql`, `create_reports_table.sql`) rather than a migrations framework — check these before assuming a column exists.

### MCP tools (`app/mcp_server.py`)
Ten tools are registered in `handle_list_tools`: `get_visibility_report`, `get_rival_analysis` (accepts an optional `topic_filter` of space-separated keywords), `list_workstreams`, `get_top_citations`, `get_recommendations`, `trigger_aeo_analysis`, `get_content_gaps`, `analyze_topic`, `analyze_drop_root_cause`, `get_raw_ai_answer`. Workspace resolution inside `handle_call_tool` tries, in order: an injected `workspace_ref`/`workspace_id` → fuzzy match on `client_name` against `brand_name`/`domain` → domain parsed from a `url` arg → auto-provision a new workspace → fall back to the most recently active workspace. `analyze_drop_root_cause` is currently a 3-week comparison, not a real root-cause LLM analysis — treat it as a placeholder if asked to extend it.

## Frontend architecture

`frontend/src/app/page.tsx` is a single large (~2,300 line) client component containing the entire dashboard: onboarding/URL discovery, the live tracking console, overview/visibility/sentiment views, competitor analysis, content gaps, and query management. There is no router-based page split — new dashboard sections are added as state/branches within this file rather than new routes. Workspace config (API key, backend URL) persists in `localStorage`, not cookies/server session. `src/components/LiveTrackingConsole.tsx` and `src/components/EngineLogos.tsx` are the only extracted components.

The frontend talks to the backend exclusively over the `/v1` REST routes in `backend/app/routers/v1.py` (visibility, competitors, prompts, runs, workstreams, clusters/content gaps, discovery/onboarding, digests/alerts) — it does not use the MCP server; that's Slack-only.

## Known gaps

- No automated PDF report generation.
- `get_raw_ai_answer` and `get_content_gaps` can blow past the 90s MCP ceiling if they fall through to an on-demand LLM call instead of reading cached/pre-computed data (see "Non-obvious invariants" above).
- `analyze_drop_root_cause` is a placeholder (3-week comparison), not real root-cause analysis.
- No pagination on most DB queries — a potential issue at scale.

## Notes specific to this codebase

- `frontend/AGENTS.md` (referenced by `frontend/CLAUDE.md`) warns that the pinned Next.js/React versions (`next@16.2.7`, `react@19.2.4`) are ahead of typical training data — check `frontend/node_modules/next/dist/docs/` for current API shape before assuming conventional Next.js behavior.
- Root `.agents/AGENTS.md`: never write credentials outside `.env` itself (no scratch files, no debug dumps); report any credential-handling accident to the user immediately as its own message.
- **This file is maintained by Claude Code, not Antigravity.** If you're another agent working in this repo, please don't delete it as a "stray" file — it complements (not duplicates) Antigravity's own docs.
