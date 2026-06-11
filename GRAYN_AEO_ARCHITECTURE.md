# Grayn AEO: Architecture & System Documentation

> **Status:** Current implementation state prior to the OpenLens parity migration.
> **Date:** June 2026

## Overview

Grayn AEO (Answer Engine Optimization) is an analytics and monitoring platform designed to track how AI models (Answer Engines) perceive, recommend, and cite brands. It simulates user queries against popular AI models and analyzes the responses to determine brand visibility, sentiment, and competitive positioning.

## Tech Stack

- **Frontend:** Next.js (React), Tailwind CSS, Framer Motion, Lucide Icons.
- **Backend:** FastAPI (Python), Uvicorn.
- **Database:** Supabase (PostgreSQL).
- **AI Integration:** Direct API integrations via `httpx` (OpenAI, Gemini, Anthropic, Groq, DeepSeek).

## System Architecture

### 1. Frontend (`/frontend`)
The frontend is a Next.js application that provides a unified dashboard for viewing AEO metrics.
- **`src/app/page.tsx`**: The monolithic main dashboard containing the UI for:
  - Onboarding / Discovery (URL scanning)
  - Live Tracking Console (triggering runs)
  - Overview Dashboard (Visibility, Sentiment, Trends)
  - Competitor Analysis
  - Content Gaps Studio
  - Query Manager
- **State Management:** Uses React `useState` and `useEffect`. Workspace configuration (API keys, Backend URL) is persisted in `localStorage`.
- **Styling:** Highly styled with Tailwind CSS for a premium dark-mode aesthetic.

### 2. Backend (`/backend`)
A FastAPI server responsible for orchestrating AI queries, parsing responses, and computing metrics.

#### Core Modules:
- **`app/main.py`**: FastAPI application entry point, CORS configuration, and router registration.
- **`app/routers/`**:
  - `v1.py`: Main endpoints for visibility metrics, query management, onboarding discovery, and Slack integrations.
  - `internal.py`: Administrative endpoints for workspace and API key management.
- **`app/models/schemas.py`**: Pydantic models defining the API contracts (e.g., `WorkspaceOut`, `PromptCreate`, `DiscoverResult`).
- **`app/services/`**:
  - `discovery.py`: Fetches a brand's URL and uses an LLM to auto-extract the brand name, competitors, themes, and suggested queries. Includes resilient fallback mechanisms to bypass bot protection.
  - `tracking.py`: The core execution engine. Dispatches prompts to configured AI providers, triggers the evaluation (judge), and logs the raw runs.
  - `judge.py`: Uses a secondary LLM (evaluator) to analyze the raw text returned by the AI provider. It extracts sentiment, brand presence, position, and citations.
  - `scoring.py`: Aggregates the raw judge evaluations into high-level metrics (Visibility Score, Share of Voice).
- **`app/services/providers/`**: Adapters for different AI APIs (`openai_provider.py`, `gemini_provider.py`, `groq_provider.py`, `claude_provider.py`). All implement a standard `BaseProvider` interface.

### 3. Database (Supabase)
Stores the configuration and historical run data. Key tables (inferred from the codebase):
- `workspaces`: Client brands being tracked.
- `api_keys`: Authentication tokens for workspaces.
- `competitors`: Tracked competitors and their aliases.
- `prompts` / `queries`: The specific questions to ask the AIs.
- `run_logs`: Raw outputs from the AI providers.
- `evaluations`: The parsed/judged results (sentiment, presence) of the runs.

## Key Workflows

### Onboarding & Discovery
1. User enters a URL on the frontend.
2. Frontend calls `POST /v1/discover` with the URL and a requested `num_queries`.
3. Backend fetches the URL HTML (with basic `User-Agent` spoofing).
4. An LLM (usually Gemini or Groq fallback) analyzes the HTML (or just the domain if scraping fails) and returns a JSON payload containing the brand name, suggested competitors, and initial queries.

### Live Tracking (Prompt Execution)
1. User triggers a tracking run via the dashboard.
2. Frontend opens the `LiveTrackingConsole` overlay and calls `POST /v1/runs/trigger`.
3. The backend spins up background tasks (`tracking.trigger_batch_run`) that dispatch queries to all configured AI providers concurrently.
4. Frontend polls `GET /v1/runs/status` to stream live progress logs to the terminal UI.

### Evaluation Pipeline
1. **Generation:** Provider (e.g., OpenAI) answers the prompt: *"What is the best SaaS billing platform?"*
2. **Judgment:** The raw answer is passed to `judge.py`, which asks an LLM to extract JSON indicating if the target brand (e.g., "Stripe") was mentioned, its sentiment, and the URLs cited.
3. **Aggregation:** `scoring.py` computes the global visibility percentage based on the ratio of positive/neutral mentions across all runs.

## Current Limitations & Constraints
- **Data Fidelity:** We currently query official APIs. API behavior (especially for ChatGPT and Perplexity) often differs significantly from their consumer web UI (e.g., missing web-search citations).
- **Hardcoded Toggles:** Prompt tags (Intent, Persona) are hardcoded Enums rather than dynamic attributes.
- **Reporting:** No automated PDF generation capability.
- **Scheduling:** Tracking runs must be triggered manually via the UI or API; there is no persistent background cron scheduler.
