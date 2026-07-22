# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is (and isn't)

This repo contains **only two of the three systems** that make up Grayn AEO:

1. `frontend/` — Next.js dashboard (deployed to Vercel, project `grayn-aeo`).
2. `backend/` — FastAPI app (deployed to Railway) that exposes:
   - a REST API under `/v1` (`app/routers/v1.py`), consumed by `frontend/`.
   - an MCP server (`app/mcp_server.py`), consumed by an **external** Slack bot.

The Slack bot itself — event handling, Block Kit rendering, CLM, Meta/Google Ads/GA4/GSC integrations, RAG — lives in a **separate** Supabase Edge Functions project, not in this repo. From this backend's point of view, that whole system is just one MCP client calling six tools (`get_visibility_report`, `analyze_topic`, `get_rival_analysis`, `analyze_drop_root_cause`, `get_content_gaps`, `get_raw_ai_answer`, plus the long-running `trigger_aeo_analysis`). Do not assume Slack-side code (event handlers, edge functions, Block Kit) is reachable here — the closest thing to its docs is `GRAYN_FRONTEND_ARCHITECTURE.md`, which describes that *other* system, not `frontend/`.

`AEO_CARD_CONTRACTS.md` (root) is the binding contract for the six MCP tools' JSON output — if you change what any of them returns, the Slack cards on the other side will break silently unless the shape still matches this doc.

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

`app/main.py` registers four routers on one FastAPI app: `v1` (public dashboard API), `internal` (admin, gated by `X-Admin-Token`), `public_lp` (public landing-page endpoints), and the MCP `router` from `mcp_server.py`. A `lifespan` hook also starts an `AsyncIOScheduler` job that runs a weekly automated tracking batch across all workspaces (chunked, with sleeps between chunks to avoid rate limits).

**Auth model** (`app/dependencies.py`): three separate schemes coexist —
- `get_current_workspace` — Bearer key (`gk_<prefix>_<secret>`), SHA-256 hashed and looked up in `api_keys`, used by the dashboard/`v1` routes.
- `require_admin` — static `X-Admin-Token` header, used by `internal` routes.
- `verify_slack_api_key` — Bearer key checked against `GRAYN_AEO_API_KEY`, used for the Lovable/Slack-facing endpoints.

**The tracking pipeline** (the core workflow most features touch):
1. `services/discovery.py` — given a URL, scrapes it and asks an LLM to extract brand name, competitors, and suggested queries (has fallback paths for when scraping is blocked).
2. `services/tracking.py` (`trigger_batch_run`) — dispatches prompts concurrently to whichever AI providers are configured, per-engine concurrency limited by a semaphore (`{ENGINE}_MAX_CONCURRENCY` env var, default 5), with `tenacity` retry/backoff on transient failures.
3. `services/providers/*` — one adapter per AI engine (`openai_provider.py`, `gemini_provider.py`, `google_ai_provider.py`, `groq_provider.py`, `claude_provider.py`, `deepseek_provider.py`, `grok_provider.py`, `perplexity_provider.py`, `browser_provider.py`, `mock_provider.py`), all implementing the `base.py` interface and returning a uniform `EngineResult`. `get_provider()` picks the implementation based on which `*_available` flag is true in `config.py` (auto-selects on whether the API key env var is set, unless `USE_MOCK_PROVIDERS` is on).
4. `services/judge.py` — a secondary LLM pass over the raw provider response, extracting brand/competitor mentions, sentiment, and cited URLs into structured data.
5. `services/scoring.py` — aggregates judged runs into visibility score / share-of-voice / trends (`build_full_report`, `compute_historical_trend`).
6. `services/citations.py`, `services/content_analyzer.py`, `services/insights.py`, `services/brand_normalizer.py`, `services/consensus.py` — downstream analysis (citation leaderboards, content gap detection, cross-engine consensus, brand name normalization/deduping) built on top of judged run data.

Because live multi-engine scans can exceed the Slack-side 90s timeout, long scans are queued (`aeo_pending_jobs`) rather than run synchronously end-to-end when called via MCP — see `AEO_CARD_CONTRACTS.md` §7–8 before changing anything in `trigger_aeo_analysis` or the five read-only MCP tools' latency characteristics (the five reads are expected to be cache/DB reads under 5s; if one starts taking 90s, that's a regression, not a new feature).

### Database (Supabase/Postgres)
Core tables: `workspaces`, `api_keys`, `competitors`, `prompts`/`aeo_prompts`, `aeo_runs`/`run_logs` (raw provider output), `aeo_mentions`/`evaluations` (judged output, `is_target_brand` distinguishes client vs. competitor), `aeo_citations`. Schema/migrations live as loose `.sql` files at the `backend/` root (`schema.sql`, `migrate_multipass.sql`, `migration_citations.sql`, `migration_mentions_raw.sql`, `create_reports_table.sql`) rather than a migrations framework — check these before assuming a column exists.

## Frontend architecture

`frontend/src/app/page.tsx` is a single large (~2,300 line) client component containing the entire dashboard: onboarding/URL discovery, the live tracking console, overview/visibility/sentiment views, competitor analysis, content gaps, and query management. There is no router-based page split — new dashboard sections are added as state/branches within this file rather than new routes. Workspace config (API key, backend URL) persists in `localStorage`, not cookies/server session. `src/components/LiveTrackingConsole.tsx` and `src/components/EngineLogos.tsx` are the only extracted components.

The frontend talks to the backend exclusively over the `/v1` REST routes in `backend/app/routers/v1.py` (visibility, competitors, prompts, runs, workstreams, clusters/content gaps, discovery/onboarding, digests/alerts) — it does not use the MCP server; that's Slack-only.

## Notes specific to this codebase

- `frontend/AGENTS.md` (referenced by `frontend/CLAUDE.md`) warns that the pinned Next.js/React versions (`next@16.2.7`, `react@19.2.4`) are ahead of typical training data — check `frontend/node_modules/next/dist/docs/` for current API shape before assuming conventional Next.js behavior.
- Root `.agents/AGENTS.md`: never write credentials outside `.env` itself (no scratch files, no debug dumps); report any credential-handling accident to the user immediately as its own message.
