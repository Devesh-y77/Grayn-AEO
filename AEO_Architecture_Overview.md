# Grayn AEO - Architecture & Workflow Overview

## 1. What is Grayn AEO?
Grayn AEO (Answer Engine Optimization) is a platform that tracks, analyzes, and reports a brand's visibility across major AI Answer Engines (like ChatGPT, Perplexity, Claude, and Gemini). 

Instead of traditional SEO (Search Engine Optimization), AEO tells brands:
* Are AI models recommending us?
* Which specific queries do we win?
* Who are our AI competitors?
* What URLs are the AIs citing when they mention us?

The user interacts with the system entirely through a **Slack Bot**, which uses a modern conversational UI to render interactive cards.

---

## 2. High-Level Architecture

The system is built on a decoupled architecture using the **Model Context Protocol (MCP)** to connect a chat-based frontend with a Python backend.

1. **Frontend (Lovable / Slack Integration)**: Handles the Slack UI, renders Block Kit interactive cards, and processes user chat inputs. When it needs data or needs to run a scan, it calls the backend via MCP.
2. **Backend (Python FastAPI / MCP Server)**: The core engine. It exposes discrete tools (like `trigger_aeo_analysis` or `get_rival_analysis`) that the frontend can call. It orchestrates the actual LLM API calls to check visibility.
3. **Database (Supabase / PostgreSQL)**: Stores all historical tracking data, workspaces, topics, AI responses, and citations.
4. **Deployment**:
   * Frontend: Vercel / Lovable
   * Backend: Railway (Continuous Deployment from the `main` branch)

---

## 3. The Core Workflow (How a Live Scan Works)

When a user clicks **"Run a Live Scan"** or asks the bot to analyze a brand, the following sequence occurs:

1. **Trigger**: The frontend calls the `trigger_aeo_analysis` MCP tool on the backend.
2. **Discovery**: If the user didn't provide specific topics, the backend asks an LLM to dynamically generate top search queries/topics relevant to that brand's URL.
3. **Execution**: The backend orchestrates parallel requests to the configured AI Providers (OpenAI, Gemini, Perplexity, Grok, etc.).
   * *Prompt*: "What are the best [Topic]?"
4. **Extraction**: The raw text response from the AI is saved. An internal evaluator (Judge) then analyzes the text to determine:
   * Did the AI mention our target brand? (`is_target_brand = True`)
   * Did it mention competitors?
   * What URLs were cited as sources?
5. **Storage**: The results are heavily normalized and written to the Supabase database.
6. **Reporting**: The backend completes the MCP call, and the frontend renders the "AEO Pulse" or "Competitor Analysis" card in Slack.

*(Note: Because live AI queries take time, the system uses a background queue (`aeo_pending_jobs` and `aeo-job-runner`) to handle Slack's strict 90-second timeout ceiling).*

---

## 4. Database Schema (Supabase)

All data is stored in PostgreSQL via Supabase. The core tables are:

- **`workspaces`**: Represents a Slack workspace/client. Stores `brand_name` and `domain`.
- **`aeo_prompts`**: The specific topics/queries being tracked (e.g., "Best interactive learning apps for toddlers").
- **`aeo_runs`**: Represents a single execution of a prompt against a specific AI engine. 
  - Key columns: `prompt_id`, `engine`, `raw_response`, `created_at`.
- **`aeo_mentions`**: Represents a brand mentioned in a run.
  - Key columns: `run_id`, `brand_name`, `is_target_brand` (Boolean to separate the client from competitors).
- **`aeo_citations`**: The specific URLs the AI engine referenced.
  - Key columns: `run_id`, `url`, `domain`, `title`.

---

## 5. Codebase Guide (Backend)

The backend code is located in the `backend/` directory. Here are the most critical files:

### `app/mcp_server.py`
The "brain" of the integration. This file defines all the MCP endpoints the Slack bot can call.
* `trigger_aeo_analysis`: Runs the live multi-engine scan.
* `get_visibility_report`: Aggregates the AEO Pulse score.
* `get_rival_analysis`: Calculates Competitor Share of Voice (SOV).
* `list_workstreams`: Fetches the 10 most recently scanned topics.
* `get_top_citations`: Fetches a leaderboard of cited URLs/Domains for the brand.
* `get_raw_ai_answer`: Pulls the exact AI text output for the Proof Card.

### `app/services/providers/`
Contains the integrations for each AI engine.
* `base.py`: The abstract base class.
* `openai_provider.py`, `gemini_provider.py`, `grok_provider.py`: The specific API implementations that fetch answers from the respective models.

### `app/services/judge.py`
The evaluation module. It takes the raw text output from an AI provider and extracts structured data (brand mentions, competitor mentions, context) so it can be saved cleanly into `aeo_mentions`.

### `AEO_CARD_CONTRACTS.md` (Root Directory)
**CRITICAL DOCUMENT.** This file defines the exact JSON schema that the frontend Lovable components expect. If the backend returns JSON that doesn't match these contracts, the Slack cards will fail to render or show blank states.

---

## 6. Development & Deployment

- **Local Testing**: You can run the backend locally using `fastapi run app/main.py`. The MCP server is exposed via SSE (Server-Sent Events).
- **Deploying**: Any code pushed to the `main` branch of the GitHub repository is automatically picked up and deployed by **Railway**.
- **Environment Variables**: Managed in Railway and `.env`. Essential variables include `SUPABASE_URL`, `SUPABASE_KEY`, and API keys for OpenAI, Anthropic, Gemini, Grok, etc.
