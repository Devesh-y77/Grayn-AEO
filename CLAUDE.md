# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Grayn AEO (Answer Engine Optimization) tracks how AI answer engines (ChatGPT, Gemini,
Perplexity, Claude, Grok, DeepSeek, Groq...) mention and cite a brand, and scores its
visibility/share-of-voice against competitors.

This repo contains **two** of the system's pieces only:

- `backend/` — Python/FastAPI service. Owns the DB access, the AI-provider calls, the
  judging/scoring pipeline, and an MCP server that exposes 6 read-only AEO tools.
- `frontend/` — a Next.js dashboard (App Router) that talks to the backend's `/v1` REST
  API directly. It is a standalone analytics UI, separate from the Slack experience.

**The production Slack bot does not live in this repo.** It's a separate Supabase
Edge Functions project (`slack-events-handler`, `slack-interactions`, `aeo-job-runner`,
etc.) that calls this backend's MCP server over SSE for the 6 AEO tools and talks to
everything else (Meta/Google/GA4/Slack/Drive) directly. `GRAYN_FRONTEND_ARCHITECTURE.md`
documents that external system in depth with `file:line` refs into its codebase — treat
it as background context, not as files you can open here. `AEO_CARD_CONTRACTS.md` is the
contract that DOES matter from this repo's side: it defines the exact JSON shape each
MCP tool must return for the Slack cards to render, and is normative for `mcp_server.py`.
`GRAYN_AEO_ARCHITECTURE.md` and `AEO_Architecture_Overview.md` are two more overview docs
of the same system at different points in time — cross-check them against the actual code
below rather than trusting either as current truth (they disagree with each other in places).

## Commands

Backend (from `backend/`, with `venv` activated):
```
uvicorn app.main:app --reload --port 8000   # local dev server
```
Interactive docs at `/docs` when `DEBUG=true` (docs are disabled otherwise). No pytest
suite exists — the many `test_*.py` / `check_*.py` / `diag*.py` files at the backend
root are one-off manual scripts (run directly with `python <file>.py`), not a managed
test suite. Likewise, root-level scratch scripts (`fix.py`, `check_db.py`, etc.) are
ad-hoc DB/debug utilities committed alongside the app — don't treat them as part of the
application surface, and feel free to add new ones the same way rather than building a
shared test harness.

Frontend (from `frontend/`):
```
npm run dev     # dev server, http://localhost:3000
npm run build
npm run lint
```

Both services together: `docker-compose up` from the repo root (reads Supabase/provider
keys from the shell environment, not from `backend/.env`).

## Backend architecture (`backend/app/`)

- `main.py` — FastAPI entrypoint. Registers `v1`, `internal`, `public_lp`, and the MCP
  router; sets up a weekly APScheduler cron (`scheduled_tracking`, Mondays 02:00) that
  batch-runs tracking for every workspace.
- `config.py` — `Settings` (pydantic-settings, reads `.env`). Each provider has an
  `<name>_available` property that's true only if its API key is set AND
  `USE_MOCK_PROVIDERS` is false — providers silently fall back to `MockProvider` otherwise.
- `database.py` — `get_supabase()` returns a singleton client. If `SUPABASE_SERVICE_KEY`
  is set it's a real Supabase HTTP client; otherwise it falls back to `DirectPostgresClient`,
  a hand-written wrapper over `psycopg2` that mimics the Supabase query-builder API
  (`.table().select().eq().execute()`, etc.) against `DATABASE_URL`. Code in `services/`
  and `routers/` is written against the Supabase-style interface and works unmodified
  against either backend.
- `dependencies.py` — auth. `get_current_workspace` validates a workspace's `gk_<prefix>_<secret>`
  Bearer key (SHA-256 hashed, looked up in `api_keys`) for `/v1`; `require_admin` gates
  `/internal` behind a static `X-Admin-Token`; `verify_slack_api_key` gates the Slack/Lovable
  integration endpoints with `GRAYN_AEO_API_KEY`.
- `routers/v1.py` — the public per-workspace API (metrics, prompts, competitors, runs,
  discovery, reports, Slack-triggered scans). `routers/internal.py` — admin-only workspace/key
  management. `routers/public_lp.py` — unauthenticated landing-page endpoints.
- `mcp_server.py` — the MCP SSE server (`Server("grayn-aeo-mcp")`) consumed by the external
  Slack bot. Exposes `get_visibility_report`, `get_rival_analysis`, `list_workstreams`,
  `get_top_citations`, `get_recommendations`, and related tools. Every tool's JSON output
  must match `AEO_CARD_CONTRACTS.md` or the Slack card silently falls back to a plain-text
  render.
- `services/providers/` — one adapter per AI engine, all implementing `BaseProvider`
  (`base.py`). `BaseProvider.query()` wraps the abstract `_query()` with a per-engine
  concurrency semaphore (`<ENGINE>_MAX_CONCURRENCY` env var, default 5), a 90s timeout,
  and tenacity-based retry on timeouts/429s/5xx. `get_provider(engine)` is the factory —
  add a new engine there and in `EngineType` (`models/schemas.py`).
- `services/discovery.py` — given a URL, scrapes it and asks an LLM to infer brand name,
  competitors, themes, and seed queries (used for workspace onboarding).
- `services/tracking.py` — dispatches prompts to providers concurrently for a batch run.
- `services/judge.py` — evaluates a provider's raw answer with a second LLM pass to extract
  brand/competitor mentions, sentiment, position, and citations.
- `services/scoring.py` — aggregates judged runs into visibility score, share-of-voice,
  trends, and the composite `/v1/report`. Any list-membership filter here (`.in_()`) must
  go through `db_helpers.chunked_in_fetch` — Postgres/PostgREST URI-length limits have
  broken this before when passing large ID lists directly.
- `services/consensus.py`, `insights.py`, `content_analyzer.py`, `brand_normalizer.py`,
  `citations.py` — supporting analysis for multi-pass agreement, recommendations, content
  gap analysis, and brand/competitor name matching respectively.

## Frontend architecture (`frontend/src/`)

Small Next.js App Router project: `app/page.tsx` is the single dashboard page (onboarding/
discovery, live tracking console, visibility/sentiment/trend views, competitor analysis,
content gaps, query manager), `components/LiveTrackingConsole.tsx` is the overlay that
triggers a run and polls `/v1/runs/status` for progress. Workspace config (backend URL,
API key) is kept in `localStorage`, not server-side session state.

Note: `frontend/AGENTS.md` claims this Next.js version has training-data-breaking API
changes and points at `node_modules/next/dist/docs/`. Verify against the installed
`next` version in `package.json` before assuming any specific API differs from what you
already know.

## Database

Schema lives in `backend/schema.sql`. Core tables: `workspaces`, `brands`, `api_keys`,
`aeo_prompts`, `aeo_competitors`, `aeo_runs` (one row per prompt × engine execution),
`aeo_mentions` (brand/competitor mentions extracted per run, `is_target_brand` splits
client vs. competitor), `aeo_citations` (URLs cited per run), `aeo_brand_content`,
`aeo_clusters`, `aeo_keyword_volumes`, `aeo_digests`. Loose `migration_*.sql` /
`migrate_*.py` files at the backend root are one-off migrations applied manually, not a
managed migration chain — check `schema.sql` for current ground truth, not the migration
files' history.
