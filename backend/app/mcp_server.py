"""
Grayn AEO — MCP Server

Exposes AEO visibility data to Claude Desktop and Cursor via Model Context Protocol.
"""
import asyncio
import json
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from app.services.db_helpers import chunked_in_fetch

from fastapi import APIRouter, Request, HTTPException
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

server = Server("grayn-aeo-mcp")

# In-memory cache to remember the last searched URL per workspace
LAST_SEARCHED_URLS: dict[str, str] = {}
LAST_SEARCHED_TOPICS: dict[str, str] = {}
LAST_SEARCHED_CITATIONS: dict[str, list[str]] = {}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available AEO tracking tools."""
    return [
        types.Tool(
            name="get_visibility_report",
            description="Get the aggregate AI visibility report and pulse score. Use for: e.g., 'show me my visibility', 'how is my brand doing'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., the last scanned URL or brand). If you absolutely don't know it, ask the user (e.g., 'netflix')."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="get_rival_analysis",
            description="Get competitor analysis across multiple topics to see where they are winning. Use for: e.g., 'who are my competitors', 'show rival analysis'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_filter": {
                        "type": "string",
                        "description": "Optional. Space-separated keywords to filter topics (e.g., 'streaming')."
                    },
                    "competitor_name": {
                        "type": "string",
                        "description": "Optional. The name of the specific competitor to analyze. NEVER put the user's own brand name here. Leave blank for a general overview."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., 'netflix')."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="list_workstreams",
            description="List the topics (also known as queries, search terms, or workstreams) currently being tracked for the brand. Use for: e.g., 'what queries are we tracking', 'list workstreams'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., 'netflix')."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="get_top_citations",
            description="Get a list of the top domains and URLs that are cited most frequently by AI engines when referencing this brand. Use for: e.g., 'what sites mention us most', 'show top citations'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., 'netflix')."
                    }
                },
                "required": ["client_name"]
            }
        ),
        # TODO: implement get_recommendations (currently queries non-existent
        # table — removed from tool list until implemented)
        types.Tool(
            name="trigger_aeo_analysis",
            description="Run a live AEO analysis by dynamically discovering queries for a URL and checking AI engine visibility. Use for: e.g., 'run a live scan for netflix.com', 'trigger analysis'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the brand/company to analyze (e.g., 'https://netflix.com')"
                    },
                    "location": {
                        "type": "string",
                        "description": "The geographic location to simulate searches from (e.g., 'New York')"
                    },
                    "queries": {
                        "type": "integer",
                        "description": "Number of queries to discover and track (e.g., 5)"
                    },
                    "models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional. List of AI models to check (e.g., ['gemini', 'openai'])"
                    },
                    "passes": {
                        "type": "integer",
                        "description": "Optional. Number of multi-pass iterations per query/engine (default: 3)."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The brand name or domain. The agent must always pass this."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="get_content_gaps",
            description="Generate a strategic content gap brief by analyzing top competitor URLs for a given topic. Use for: e.g., 'what content should we write for [topic]', 'show content gaps'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional. The target topic or keyword to analyze (e.g., 'what is the best streaming service'). Leave blank to use the topic from your last live analysis."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The brand name or domain. The agent must always pass this."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="analyze_topic",
            description="Deep dive into a specific topic to see which engines cite the brand and who the top competitors are. Use for: e.g., 'analyze topic [topic]', 'how did we do on [topic]'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "The name of the topic/keyword to analyze (e.g., 'what is the best streaming service')."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The brand name or domain. The agent must always pass this."
                    }
                },
                "required": ["topic_name", "client_name"]
            }
        ),
        # TODO: implement drop root cause analysis. This tool was previously
        # listed here but had no handler in handle_call_tool at all — every
        # call returned "Unknown tool: analyze_drop_root_cause". Removed from
        # the advertised tool list until it's actually implemented, so the
        # agent never routes to it. See Issue 5.
        types.Tool(
            name="get_raw_ai_answer",
            description="Fetch the exact raw text output generated by an AI engine for a specific topic, serving as proof. Use for: e.g., 'show me the raw AI output for [topic]', 'what did chatgpt say exactly'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic that was queried."
                    },
                    "engine": {
                        "type": "string",
                        "description": "The engine (e.g. chatgpt, perplexity) to fetch proof for."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., 'netflix')."
                    }
                },
                "required": ["topic", "engine", "client_name"]
            }
        )
    ]

async def _generate_topic_gap(topic_text, target_brand, winners, sample_losing_answer):
    """
    Best-effort one-line "what's missing" analysis for a Topic card (P3 of
    the UI-alignment spec). Given a real AI answer that did NOT mention the
    target brand for this topic, ask a cheap/fast model what specific angle
    that answer covers which the target brand would need to address to
    compete.

    Never raises and never blocks the scan on a slow/unavailable model —
    this is a nice-to-have annotation, not a required field. Returns None
    on any failure or timeout, in which case callers should simply omit the
    "gap" field rather than surface an error.
    """
    if not sample_losing_answer or not winners:
        return None
    try:
        from app.config import get_settings
        settings = get_settings()
        if not settings.deepseek_available:
            return None

        prompt = (
            f"Target brand: {target_brand}\n"
            f"Topic: {topic_text}\n"
            f"Brands mentioned instead: {', '.join(winners[:3])}\n\n"
            f"Here is a real AI answer to this query that did NOT mention {target_brand}:\n"
            f"---\n{sample_losing_answer[:800]}\n---\n\n"
            f"In one short sentence (under 25 words), what specific angle or "
            f"content does this answer cover that a page about '{target_brand}' "
            f"for this topic would need to address to compete? Be concrete, not generic."
        )

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80,
            ),
            timeout=15.0,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None


async def resolve_active_brand(db, workspace_id, client_name_hint=None):
    """
    Resolve which brand's data a read tool should show for this workspace.

    One workspace = one account, but an account can scan many different
    brands over time (Nike, Flipkart, WonJo Kids, ...) — brand identity
    lives on aeo_prompts.brand_name, not on the workspace row. Resolution
    order:
      1. client_name_hint, if it matches a brand previously scanned here
      2. the most recently scanned brand for this workspace
      3. workspaces.brand_name/domain, but ONLY if nothing has ever been
         scanned here yet (aeo_prompts is completely empty)

    Returns (brand_name, domain, prompt_ids) — prompt_ids is the full set
    of aeo_prompts.id belonging to the resolved brand, for callers to scope
    every downstream aeo_runs/aeo_mentions/aeo_citations query with, so one
    brand's data never blends into another's response.
    """
    rows = (
        await asyncio.to_thread(
            lambda: db.table("aeo_prompts")
            .select("id, brand_name, domain, created_at")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
            .execute()
        )
    ).data or []

    if not rows:
        ws_res = await asyncio.to_thread(
            lambda: db.table("workspaces").select("brand_name, domain").eq("id", workspace_id).execute()
        )
        ws = (ws_res.data or [{}])[0]
        return ws.get("brand_name"), ws.get("domain"), []

    chosen_brand = None
    if client_name_hint:
        c_lower = client_name_hint.lower().strip()
        for r in rows:
            if (r.get("brand_name") or "").lower().strip() == c_lower:
                chosen_brand = r["brand_name"]
                break
        if not chosen_brand:
            for r in rows:
                b = (r.get("brand_name") or "").lower()
                if b and (c_lower in b or b in c_lower):
                    chosen_brand = r["brand_name"]
                    break

    if not chosen_brand:
        # No hint, or it didn't match anything scanned here — default to
        # the most recently scanned brand (rows is already ordered desc).
        chosen_brand = rows[0]["brand_name"]

    brand_domain = next((r["domain"] for r in rows if r["brand_name"] == chosen_brand), None)
    prompt_ids = [r["id"] for r in rows if r["brand_name"] == chosen_brand]
    return chosen_brand, brand_domain, prompt_ids


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Execute AEO tool."""
    from app.database import get_supabase

    db = get_supabase()
    # Frontend injects client_name, target_brand, brand, url, domain, workspace_ref
    client_name = (arguments.get("client_name") or arguments.get("target_brand") or arguments.get("brand")) if arguments else None
    url = (arguments.get("url") or arguments.get("domain")) if arguments else None
    # Lovable dispatcher will inject workspace_ref from prod DB
    injected_workspace_id = (arguments.get("workspace_ref") or arguments.get("workspace_id")) if arguments else None
    workspace_data = None
    
    # 1. System-injected workspace ID (most secure/accurate)
    if injected_workspace_id:
        ws_res = await asyncio.to_thread(lambda: db.table("workspaces").select("id, brand_name, domain").eq("id", injected_workspace_id).execute())
        if ws_res.data:
            workspace_data = ws_res.data[0]
            
    # 2. Match by client_name — exact match first, fuzzy substring only as last resort
    if not workspace_data and client_name:
        c_lower = client_name.lower().strip()
        ws_res = await asyncio.to_thread(lambda: db.table("workspaces").select("id, brand_name, domain").execute())
        all_workspaces = ws_res.data or []

        # 2a. Exact match on brand_name
        for ws in all_workspaces:
            if (ws.get("brand_name") or "").lower().strip() == c_lower:
                workspace_data = ws
                break

        # 2b. Exact match on domain (normalized — strip scheme/www/trailing slash)
        if not workspace_data:
            for ws in all_workspaces:
                ws_domain = (ws.get("domain") or "").lower().strip()
                ws_domain_normalized = ws_domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                if ws_domain_normalized == c_lower:
                    workspace_data = ws
                    break

        # 2c. Fuzzy substring match — last resort only, may be ambiguous across
        # workspaces sharing a brand name (see Issue 4 audit)
        if not workspace_data:
            for ws in all_workspaces:
                ws_brand = ws.get("brand_name") or ""
                ws_domain = ws.get("domain") or ""
                if (ws_brand and c_lower in ws_brand.lower()) or (ws_domain and c_lower in ws_domain.lower()) or (ws_brand and ws_brand.lower() in c_lower) or (ws_domain and ws_domain.lower() in c_lower):
                    workspace_data = ws
                    break
                    
    if not workspace_data and url:
        from urllib.parse import urlparse
        parsed_uri = urlparse(url if "://" in url else "https://" + url)
        domain = parsed_uri.netloc.replace("www.", "").lower()
        
        ws_res = await asyncio.to_thread(lambda: db.table("workspaces").select("id, brand_name, domain").ilike("domain", f"%{domain}%").execute())
        if ws_res.data:
            workspace_data = ws_res.data[0]
        else:
            # Auto-provision a new workspace for this domain
            brand_name = client_name or domain.split(".")[0].title()
            payload = {
                "brand_name": brand_name,
                "domain": domain
            }
            # Keep IDs perfectly synced across prod and staging databases!
            if injected_workspace_id:
                payload["id"] = injected_workspace_id
                
            new_ws = await asyncio.to_thread(lambda: db.table("workspaces").insert(payload).execute())
            if new_ws.data:
                workspace_data = new_ws.data[0]
                
    if not workspace_data and client_name:
        return [types.TextContent(type="text", text=f"I couldn't find any existing tracking data for '{client_name}'. To get started, I can run a fresh live AEO scan. What is the website URL for {client_name}?")]

    # No silent "most recently active workspace" fallback — resolving to the
    # wrong workspace here means leaking one client's data to another (Issue 4).
    # If we can't confidently resolve a workspace, ask instead of guessing.
    if not workspace_data:
        return [types.TextContent(type="text", text="I need to know which brand or website you're asking about before I can look this up — please specify the brand name or URL.")]
    
    workspace_id = workspace_data["id"]

    # Resolve which brand's data this call should see (see resolve_active_brand
    # docstring — one workspace can hold many brands' scans). trigger_aeo_analysis
    # resolves its own brand from the scanned URL instead and doesn't use this.
    active_brand_name, active_brand_domain, active_prompt_ids = await resolve_active_brand(
        db, workspace_id, client_name_hint=client_name
    )

    try:
        if name == "get_visibility_report":
            from app.services.scoring import compute_visibility
            vis = compute_visibility(db, workspace_id, prompt_ids=active_prompt_ids)
            
            if not vis.iso_week:
                return [types.TextContent(type="text", text=json.dumps({"error": "No recent tracking scans found."}))]
                
            # Find the highlight: which engine grew the most?
            highlight = "No significant changes this week."
            
            from datetime import date as _date, timedelta
            year, week_num = int(vis.iso_week[:4]), int(vis.iso_week.split("W")[1])
            d = _date.fromisocalendar(year, week_num, 1) - timedelta(days=7)
            prev_week = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
                
            prev_vis = compute_visibility(db, workspace_id, prev_week, prompt_ids=active_prompt_ids)

            if prev_vis and prev_vis.per_engine and vis.per_engine:
                max_growth = 0
                max_engine = None
                for eng, pct in vis.per_engine.items():
                    prev_pct = prev_vis.per_engine.get(eng, 0)
                    if pct - prev_pct > max_growth:
                        max_growth = pct - prev_pct
                        max_engine = eng
                if max_engine and max_growth > 0:
                    highlight = f"{max_engine.title().replace('_', ' ')} jumped +{round(max_growth)} points vs last week."

            brand_display = (active_brand_name or "").title()
            if not brand_display:
                brand_display = "Your Brand"
            
            if prev_vis and prev_vis.per_engine:
                actual_delta = round(vis.visibility_pct - prev_vis.visibility_pct)
                summary_text = f"**{brand_display}** tracking summary. {'+' if actual_delta > 0 else ''}{actual_delta} pts vs last week.\nOne to mention: **{highlight}**"
            else:
                summary_text = f"**{brand_display}** baseline established today. (No historical data to compare against yet).\nOne to mention: **{highlight}**"
                
            payload = {
                "overall_score": int(round(vis.visibility_pct)),
                "summary": summary_text,
                "highlight": highlight,
                "engines": []
            }

            # "Cited in X of Y" — the design's Pulse card framing, in addition
            # to the plain percentage. NOTE: this counts topic x engine scan
            # groups this week (Y = total_groups), which is NOT the same
            # number as footer.total_tracked below (distinct tracked
            # prompts/topics, engine-independent) — deliberately named
            # differently (total_groups vs total_tracked) so a renderer
            # never confuses the two.
            if vis.mentioned_groups is not None and vis.total_groups is not None:
                payload["cited_in"] = vis.mentioned_groups
                payload["total_groups"] = vis.total_groups

            payload["footer"] = {
                "total_tracked": len(active_prompt_ids),
                "engine_count": len(vis.per_engine),
                "iso_week": vis.iso_week,
            }

            for eng, pct in vis.per_engine.items():
                eng_data = {
                    "name": eng.title().replace('_', ' '),
                    "score": int(round(pct))
                }
                if vis.engine_confidences and eng in vis.engine_confidences:
                    eng_data["confidence"] = vis.engine_confidences[eng]

                if prev_vis and prev_vis.per_engine and eng in prev_vis.per_engine:
                    eng_data["delta"] = int(round(pct - prev_vis.per_engine[eng]))

                payload["engines"].append(eng_data)

            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "analyze_topic":
            topic_name = arguments.get("topic_name")
            if not topic_name:
                return [types.TextContent(type="text", text=json.dumps({"error": "topic_name is required"}))]

            if not active_prompt_ids:
                return [types.TextContent(type="text", text=json.dumps({"error": "No recent runs found"}))]

            runs = (await asyncio.to_thread(lambda: db.table("aeo_runs").select("id, engine, scan_group_id, status, raw_response, aeo_prompts!inner(prompt_text)").eq("workspace_id", workspace_id).in_("prompt_id", active_prompt_ids).order("created_at", desc=True).limit(200).execute())).data
            if not runs:
                return [types.TextContent(type="text", text=json.dumps({"error": "No recent runs found"}))]

            topic_keywords = topic_name.lower().split()
            topic_runs = [r for r in runs if r.get("aeo_prompts") and all(kw in r["aeo_prompts"].get("prompt_text", "").lower() for kw in topic_keywords)]
            if not topic_runs:
                return [types.TextContent(type="text", text=json.dumps({"error": f"No recent runs found for topic '{topic_name}'"}))]
                
            # Filter to just the most recent scan_group_id per engine
            engine_latest_group = {}
            for r in topic_runs:
                eng = r["engine"]
                group = r.get("scan_group_id") or r.get("id")
                if eng not in engine_latest_group:
                    engine_latest_group[eng] = group
            
            # Keep only the runs that belong to the latest scan group for their engine
            latest_runs = [r for r in topic_runs if (r.get("scan_group_id") or r.get("id")) == engine_latest_group.get(r["engine"])]
            run_ids = [r["id"] for r in latest_runs]
            
            mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", run_ids)
            mentioned_run_ids = set(m["run_id"] for m in mentions if m.get("is_target_brand"))
            
            from app.services.consensus import compute_group_metrics
            
            engines_won = []
            competitor_tally = {}
            
            # Group by engine for display
            engine_runs = {}
            for r in latest_runs:
                eng = r["engine"]
                if eng not in engine_runs:
                    engine_runs[eng] = []
                engine_runs[eng].append(r)
                
            sample_losing_answer = None
            for eng, e_runs in engine_runs.items():
                rate, groups, _ = compute_group_metrics(e_runs, mentioned_run_ids)
                cited = rate >= 0.5  # Consider it a win if >= 50% of passes cited (standardized, see Issue 10)
                engines_won.append({
                    "engine": eng.title().replace("_", " "),
                    "cited": cited
                })
                if not cited and sample_losing_answer is None:
                    sample_losing_answer = next((r.get("raw_response") for r in e_runs if r.get("raw_response")), None)

            for m in mentions:
                if not m.get("is_target_brand"):
                    c_name = m.get("brand_name", "Unknown")
                    competitor_tally[c_name] = competitor_tally.get(c_name, 0) + 1

            sorted_comps = sorted(competitor_tally.items(), key=lambda x: x[1], reverse=True)
            top_competitors = [c[0] for c in sorted_comps[:3]]

            total_rate, total_groups, _ = compute_group_metrics(latest_runs, mentioned_run_ids)
            visibility_pct = int((total_rate / total_groups) * 100) if total_groups else 0

            engines_hit = [e["engine"] for e in engines_won if e["cited"]]
            engines_missed = [e["engine"] for e in engines_won if not e["cited"]]

            gap = None
            if engines_missed and sample_losing_answer:
                gap = await _generate_topic_gap(topic_name, active_brand_name, top_competitors, sample_losing_answer)

            payload = {
                "topic": topic_name,
                "visibility": visibility_pct,
                "winners": top_competitors,
                "engines_hit": engines_hit,
                "engines_missed": engines_missed,
                "gap": gap,
                "summary": (
                    f"Cited by {len(engines_hit)} of {len(engines_won)} engines for this topic."
                    if engines_hit else
                    f"Not cited by any of {len(engines_won)} engines checked for this topic."
                ),
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_rival_analysis":
            competitor_name = arguments.get("competitor_name")
            target_brand_arg = arguments.get("target_brand")
            topic_filter = arguments.get("topic_filter")

            if not active_prompt_ids:
                return [types.TextContent(type="text", text="I don't see any recent tracking scans for your brand, so I can't analyze competitors yet. Would you like me to run a live visibility scan right now?")]

            runs = (await asyncio.to_thread(lambda: db.table("aeo_runs").select("id, prompt_id, engine, created_at, scan_group_id, status").eq("workspace_id", workspace_id).in_("prompt_id", active_prompt_ids).order("created_at", desc=True).execute())).data
            if not runs:
                return [types.TextContent(type="text", text="I don't see any recent tracking scans for your brand, so I can't analyze competitors yet. Would you like me to run a live visibility scan right now?")]
                
                
            active_run_ids = set()
            if target_brand_arg:
                ws_run_ids = [r["id"] for r in runs]
                target_mentions = chunked_in_fetch(db, "aeo_mentions", "run_id", workspace_id, "run_id", ws_run_ids, extra_filters={"is_target_brand": True, "brand_name": target_brand_arg})
                active_run_ids = {m["run_id"] for m in target_mentions}
                
            if not active_run_ids:
                # Default to the most recent scan session (within 5 minutes of the latest run)
                # This also acts as a fallback if the target_brand had 0% visibility and wasn't found in mentions.
                latest_time_str = runs[0]["created_at"].replace('Z', '+00:00')
                latest_time = datetime.fromisoformat(latest_time_str)
                for r in runs:
                    r_time_str = r["created_at"].replace('Z', '+00:00')
                    r_time = datetime.fromisoformat(r_time_str)
                    if (latest_time - r_time).total_seconds() < 300:
                        active_run_ids.add(r["id"])
                        
            if not active_run_ids:
                return [types.TextContent(type="text", text=f"*No tracking data found.*")]
                
            runs = [r for r in runs if r["id"] in active_run_ids]
            run_ids = [r["id"] for r in runs]
            prompts = (await asyncio.to_thread(lambda: db.table("aeo_prompts").select("id, prompt_text").eq("workspace_id", workspace_id).in_("id", active_prompt_ids).execute())).data
            prompt_map = {p["id"]: p["prompt_text"] for p in prompts}
            
            if topic_filter:
                filter_kws = topic_filter.lower().split()
                runs = [r for r in runs if r.get("prompt_id") in prompt_map and all(kw in prompt_map[r["prompt_id"]].lower() for kw in filter_kws)]
                run_ids = [r["id"] for r in runs]
                if not runs:
                    return [types.TextContent(type="text", text=f"*No tracking data found matching topic filter '{topic_filter}'.*")]
            
            mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", run_ids)
            
            # Prevent AI from mistakenly passing the user's own brand or generic query terms as a competitor name
            if competitor_name:
                ws_brand = (active_brand_name or "").lower()
                ws_domain = (active_brand_domain or "").lower()
                c_lower = competitor_name.lower().strip()
                generic_terms = {"ai search", "search", "ai", "all", "competitors", "competitor", "overview", "general", "landscape", "analysis"}
                if c_lower in generic_terms or (ws_brand and c_lower in ws_brand) or (ws_domain and c_lower in ws_domain) or (ws_domain and ws_domain in c_lower) or (ws_brand and ws_brand in c_lower):
                    competitor_name = None
                
            from app.services.consensus import compute_group_metrics, group_runs_by_scan_group, get_group_confidence
            
            # Helper logic to return general overview payload
            def _build_overview_payload():
                comp_to_mentions = defaultdict(set)
                for m in mentions:
                    if not m.get("is_target_brand"):
                        c_name = m.get("brand_name", "Unknown")
                        comp_to_mentions[c_name].add(m["run_id"])
                            
                if not comp_to_mentions:
                    return [types.TextContent(type="text", text="*No competitors found in the data.*")]
                    
                comp_sov_scores = {}
                runs_grouped = group_runs_by_scan_group(runs)
                for comp, c_run_ids in comp_to_mentions.items():
                    rate, groups, _ = compute_group_metrics(runs, c_run_ids)
                    if groups > 0:
                        conf_sum = sum(get_group_confidence(g, c_run_ids) for g in runs_grouped.values())
                        avg_conf = int(round(conf_sum / groups)) if groups else 100
                        comp_sov_scores[comp] = {
                            "share_of_voice": int(round((rate / groups) * 100)),
                            "confidence": avg_conf
                        }
                    
                sorted_comps = sorted(comp_sov_scores.items(), key=lambda x: x[1]["share_of_voice"], reverse=True)
                
                payload = {
                    "summary": "Competitor AEO Landscape (Overview)",
                    "rows": [
                        {
                            "name": comp, 
                            "share_of_voice": data["share_of_voice"], 
                            "delta": 0,
                            "confidence": data["confidence"]
                        }
                        for comp, data in sorted_comps[:10]
                    ]
                }
                return [types.TextContent(type="text", text=json.dumps(payload))]

            if not competitor_name:
                return _build_overview_payload()
                
            # Specific competitor analysis
            c_topic_run_ids = defaultdict(set)
            for m in mentions:
                if m.get("brand_name", "").lower() == competitor_name.lower():
                    run = next((r for r in runs if r["id"] == m["run_id"]), None)
                    if run:
                        topic = prompt_map.get(run["prompt_id"], "Unknown Topic")
                        c_topic_run_ids[topic].add(run["id"])
                        
            if not c_topic_run_ids:
                # If specific competitor was not found in mentions, fallback to overview payload
                return _build_overview_payload()
                
            topic_runs = defaultdict(list)
            for r in runs:
                topic = prompt_map.get(r["prompt_id"], "Unknown Topic")
                topic_runs[topic].append(r)
                
            topic_sov_scores = {}
            for topic, c_run_ids in c_topic_run_ids.items():
                t_runs = topic_runs[topic]
                rate, groups, _ = compute_group_metrics(t_runs, c_run_ids)
                if groups > 0:
                    runs_grouped = group_runs_by_scan_group(t_runs)
                    conf_sum = sum(get_group_confidence(g, c_run_ids) for g in runs_grouped.values())
                    avg_conf = int(round(conf_sum / groups)) if groups else 100
                    topic_sov_scores[topic] = {
                        "share_of_voice": int(round((rate / groups) * 100)),
                        "confidence": avg_conf
                    }
                    
            sorted_topics = sorted(topic_sov_scores.items(), key=lambda x: x[1]["share_of_voice"], reverse=True)

            # Vol/mo per topic, when available. NOTE: aeo_keyword_volumes is
            # currently empty in production (no keyword-volume provider is
            # wired up yet) — this returns null for every topic until that
            # table is populated by some future integration; the lookup
            # itself is correct and ready for when it is.
            volume_rows = (await asyncio.to_thread(
                lambda: db.table("aeo_keyword_volumes").select("keyword, search_volume").eq("workspace_id", workspace_id).execute()
            )).data or []
            volume_map = {v["keyword"].lower().strip(): v["search_volume"] for v in volume_rows if v.get("keyword")}

            payload = {
                "competitor": competitor_name.title(),
                "summary": f"Won {len(topic_sov_scores)} topics. Biggest opportunity: {sorted_topics[0][0]}",
                "rows": []
            }
            for topic, data in sorted_topics:
                payload["rows"].append({
                    "name": topic,
                    "share_of_voice": data["share_of_voice"],
                    "confidence": data["confidence"],
                    "delta": 0,
                    "volume": volume_map.get(topic.lower().strip()),
                })
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "list_workstreams":
            if not active_prompt_ids:
                return [types.TextContent(type="text", text="No topics are currently being tracked. Try running a live AEO scan first!")]

            # Fetch the most recent runs to get only recently tracked topics
            # (brand-scoped via active_prompt_ids — otherwise this could show
            # another brand's topics from the same workspace/account)
            runs = (await asyncio.to_thread(lambda: db.table("aeo_runs").select("prompt_id, created_at, aeo_prompts(prompt_text)").eq("workspace_id", workspace_id).in_("prompt_id", active_prompt_ids).order("created_at", desc=True).limit(200).execute())).data

            if not runs:
                return [types.TextContent(type="text", text="No topics are currently being tracked. Try running a live AEO scan first!")]
                
            # Filter to only include the most recent scan session (within 5 mins of latest run)
            latest_time = datetime.fromisoformat(runs[0]["created_at"].replace('Z', '+00:00'))
            recent_runs = [r for r in runs if (latest_time - datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))).total_seconds() < 300]
                
            unique_topics = []
            for r in recent_runs:
                p_data = r.get("aeo_prompts")
                if p_data:
                    # Handle both dictionary and list return formats from Supabase joins
                    p_text = p_data.get("prompt_text") if isinstance(p_data, dict) else p_data[0].get("prompt_text") if p_data else None
                    if p_text and p_text not in unique_topics:
                        unique_topics.append(p_text)
                        if len(unique_topics) >= 10:  # Cap at 10 most recent to prevent massive lists
                            break
                            
            md = "**Recently Tracked Topics:**\n\n"
            for t in unique_topics:
                md += f"• {t}\n"
            return [types.TextContent(type="text", text=md)]
            
        elif name == "get_raw_ai_answer":
            topic = arguments.get("topic")
            engine = arguments.get("engine")
            
            if not topic or not engine:
                return [types.TextContent(type="text", text=json.dumps({"error": "Both topic and engine are required."}))]

            if not active_prompt_ids:
                return [types.TextContent(type="text", text=json.dumps({"error": f"No tracking data found for topic: {topic}"}))]

            prompts = (await asyncio.to_thread(lambda: db.table("aeo_prompts").select("id").eq("workspace_id", workspace_id).in_("id", active_prompt_ids).ilike("prompt_text", f"%{topic}%").limit(1).execute())).data
            if not prompts:
                return [types.TextContent(type="text", text=json.dumps({"error": f"No tracking data found for topic: {topic}"}))]
                
            prompt_id = prompts[0]["id"]
            runs = (await asyncio.to_thread(lambda: db.table("aeo_runs").select("id, raw_response").eq("prompt_id", prompt_id).ilike("engine", f"%{engine}%").order("created_at", desc=True).limit(1).execute())).data
            
            if not runs or not runs[0].get("raw_response"):
                return [types.TextContent(type="text", text=json.dumps({"error": f"No raw AI answer found for {topic} on {engine}. It might be from an older scan before we started saving raw text!"}))]
                
            run_id = runs[0]["id"]
            raw_text = runs[0]["raw_response"]
            
            citations = (await asyncio.to_thread(lambda: db.table("aeo_citations").select("url").eq("run_id", run_id).execute())).data
            citation_urls = [c["url"] for c in citations if c.get("url")] if citations else []
            
            payload = {
                "topic": topic.title(),
                "engine": engine.title(),
                "answer": raw_text,
                "sources": citation_urls
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_top_citations":
            # Redesigned as an outreach-target ranking (Sources card — see
            # AEO_CARD_CONTRACTS.md): "which authoritative sources are cited
            # a lot across our tracked topics, and do we already have a
            # citation there or not" — rather than the old framing, which
            # only ever showed sources that ALREADY cite us and couldn't
            # answer "where should we pursue coverage."
            if not active_prompt_ids:
                return [types.TextContent(type="text", text=json.dumps({"error": "No tracking data found yet for this brand."}))]

            # ALL runs for this brand's tracked topics — the full
            # competitive citation landscape, not just runs that happened
            # to mention us.
            brand_runs = chunked_in_fetch(db, "aeo_runs", "id, created_at", workspace_id, "prompt_id", active_prompt_ids)
            if not brand_runs:
                return [types.TextContent(type="text", text=json.dumps({"error": "No tracking data found yet for this brand."}))]
            brand_runs = sorted(brand_runs, key=lambda x: x["created_at"], reverse=True)

            # Scope to the most recent scan session (within 5 min of the latest run)
            latest_time = datetime.fromisoformat(brand_runs[0]["created_at"].replace('Z', '+00:00'))
            recent_run_ids = [r["id"] for r in brand_runs if (latest_time - datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))).total_seconds() < 300]

            # Which of these runs actually mentioned the target brand —
            # used purely to compute the "cites_you" flag per domain below.
            target_mentions = chunked_in_fetch(db, "aeo_mentions", "run_id", workspace_id, "run_id", recent_run_ids, extra_filters={"is_target_brand": True})
            target_run_ids = set(m["run_id"] for m in target_mentions)

            citations = chunked_in_fetch(db, "aeo_citations", "url, domain, run_id", workspace_id, "run_id", recent_run_ids)
            if not citations:
                return [types.TextContent(type="text", text=json.dumps({"error": "No citation URLs found in the latest AI engine responses for these topics."}))]

            comp = chunked_in_fetch(db, "aeo_mentions", "brand_name", workspace_id, "run_id", recent_run_ids, extra_filters={"is_target_brand": False})
            import re
            comp_slugs = set(re.sub(r'[^a-z0-9]', '', c["brand_name"].lower()) for c in comp if c.get("brand_name"))

            domain_total = Counter()
            domain_cites_you = {}
            total_citation_count = 0

            for c in citations:
                d = c.get("domain")
                if not d or d == "unknown":
                    continue
                # Competitor-owned domains aren't real outreach opportunities
                # (you can't pursue a citation on a rival's own website).
                if any(slug in d.lower() for slug in comp_slugs if len(slug) > 2):
                    continue
                domain_total[d] += 1
                total_citation_count += 1
                if c.get("run_id") in target_run_ids:
                    domain_cites_you[d] = True

            if total_citation_count == 0:
                return [types.TextContent(type="text", text=json.dumps({"error": "No third-party citation sources found for these topics (only competitor-owned domains were cited)."}))]

            top_domains = domain_total.most_common(10)
            rows = [
                {
                    "domain": d,
                    "share_of_citations": int(round((count / total_citation_count) * 100)),
                    "cites_you": bool(domain_cites_you.get(d, False)),
                }
                for d, count in top_domains
            ]

            # Outreach priority: highest-share domains that don't cite us yet.
            best_roi = [r["domain"] for r in rows if not r["cites_you"]][:3]

            target_brand_name = active_brand_name or "your brand"
            payload = {
                "summary": f"Top cited sources across {target_brand_name}'s tracked topics",
                "rows": rows,
                "best_roi": best_roi,
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_recommendations":
            # Not implemented — queries a table that doesn't exist in the
            # production schema. Removed from handle_list_tools; this guard
            # is only for a direct call bypassing the tool list.
            return [types.TextContent(type="text", text=json.dumps({"error": "Recommendations aren't available yet. Try asking for a rival analysis or content gaps instead."}))]
            
        elif name == "trigger_aeo_analysis":
            args = arguments or {}
            url = args.get("url")
            
            # State-memory feature: fallback to the last searched URL if user didn't provide one
            if not url:
                url = LAST_SEARCHED_URLS.get(str(workspace_id))
                if not url:
                    return [types.TextContent(type="text", text="I need a website URL to run a live AEO analysis, but I couldn't find one in our history. Could you please provide the URL you'd like me to scan?")]
            
            # Save to memory for future queries
            LAST_SEARCHED_URLS[str(workspace_id)] = url
            
            location = args.get("location") or "USA"
            queries_count = args.get("queries") or 3
            models = args.get("models") or ["openai", "deepseek", "claude", "gemini", "perplexity", "grok"]
            passes = args.get("passes") or 3
            
            # Auto-scale passes down to avoid blowing the 200s scan budget.
            # Budget formula: queries * engines * passes * ~avg_seconds_per_call.
            # We cap at ~120 total calls to stay under 200s wallclock.
            raw_engine_count = len(models)  # before key-filtering; re-evaluated after
            if queries_count * raw_engine_count * passes > 120:
                passes = max(1, 120 // max(1, queries_count * raw_engine_count))
                logger.info("Auto-scaled passes to %d to stay within scan budget.", passes)
            
            # Filter out engines with missing credentials before spending any calls
            from app.config import get_settings as _get_settings
            _s = _get_settings()
            _avail_map = {
                "openai":     _s.openai_available,
                "claude":     _s.anthropic_available,
                "gemini":     _s.gemini_available,
                "groq":       _s.groq_available,
                "deepseek":   _s.deepseek_available,
                "grok":       _s.grok_available,
                "perplexity": _s.perplexity_available,
            }
            skipped = [m for m in models if not _avail_map.get(m, False)]
            models = [m for m in models if _avail_map.get(m, False)]
            if skipped:
                logger.info("Skipping engines with missing API keys: %s", skipped)
            if not models:
                return [types.TextContent(type="text", text="No engines are available — all API keys are missing. Please configure at least one provider key in your environment.")]
            
            if queries_count * len(models) * passes > 200:
                return [types.TextContent(type="text", text="Cost guard limit exceeded: max 200 total API calls allowed per scan.")]

            
            from app.services.discovery import run_discovery
            from app.services.providers.base import get_provider, EngineType
            from app.services.judge import extract_mentions_and_citations
            import uuid
            
            force_rediscovery = args.get("force_rediscovery", False)
            suggested_queries = []
            brand_name = None

            # One workspace = one account, which can scan many different
            # brands over time — brand identity lives on aeo_prompts, not on
            # the workspace row. Only reuse cached prompts that belong to
            # THIS exact domain, never another brand previously scanned
            # under the same account (see the brand-isolation redesign).
            from urllib.parse import urlparse as _urlparse
            _parsed_url = _urlparse(url if "://" in url else "https://" + url)
            _url_domain = _parsed_url.netloc.replace("www.", "").lower()

            if not force_rediscovery:
                cached_prompts = await asyncio.to_thread(
                    lambda: db.table("aeo_prompts")
                    .select("prompt_text, brand_name")
                    .eq("workspace_id", workspace_id)
                    .eq("intent", "live_scan")
                    .eq("domain", _url_domain)
                    .limit(queries_count)
                    .execute()
                )
                if cached_prompts.data:
                    suggested_queries = [p["prompt_text"] for p in cached_prompts.data]
                    brand_name = cached_prompts.data[0]["brand_name"]

            if not suggested_queries:
                discovery = await run_discovery(url, num_queries=queries_count)
                brand_name = discovery.get("brand_name", url)

                # NOTE: workspaces.brand_name/domain are intentionally never
                # written here anymore — the workspace row is the account
                # container, not a single brand's identity. Overwriting it
                # on every scan previously relabeled other brands' data
                # (e.g. an existing "Flipkart" workspace silently became
                # "WonJo Kids" after a later scan for a different domain).

                suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])]
                # Clear stale prompts for THIS brand/domain only — never
                # touch other brands tracked under the same workspace.
                try:
                    await asyncio.to_thread(
                        lambda: db.table("aeo_prompts")
                        .delete()
                        .eq("workspace_id", workspace_id)
                        .eq("intent", "live_scan")
                        .eq("domain", _url_domain)
                        .execute()
                    )
                except Exception:
                    pass

            # De-duplicate by normalized text. The underlying table can hold
            # case-variant duplicates for the same logical topic (e.g. legacy
            # rows from before prompt_text was consistently .strip().lower()'d
            # everywhere) — without this, the cache-reuse fetch above can pull
            # in both variants as if they were different topics, doubling the
            # cost of the scan and showing the same topic twice in the report
            # with two independently-judged (and sometimes different-looking)
            # results.
            seen_normalized = set()
            deduped_queries = []
            for q in suggested_queries:
                norm = q.strip().lower()
                if norm not in seen_normalized:
                    seen_normalized.add(norm)
                    deduped_queries.append(q)
            suggested_queries = deduped_queries

            iso_week = f"{datetime.now().year}-W{datetime.now().isocalendar()[1]:02d}"

            # Batch the brand lookup ONCE for the whole scan, and normalize
            # the target brand once up front — both closed over by
            # run_single below. Previously normalize() was called twice per
            # mention (once for the mention, once redundantly for the
            # target brand every single time), each call re-fetching the
            # entire brands table and serializing through one lock. Across
            # a scan with hundreds of mentions this caused an 8-minute
            # production hang. See brand_normalizer.py's performance fix.
            from app.services.brand_normalizer import normalize, load_brand_cache
            brand_cache = await load_brand_cache(str(workspace_id), db)
            canonical_brand_name, _ = await normalize(brand_name, str(workspace_id), db, brand_cache=brand_cache)

            prompts_cache = {}
            for q in suggested_queries:
                p_insert = db.table("aeo_prompts").upsert({
                    "workspace_id": workspace_id,
                    "prompt_text": q.strip().lower(),
                    "intent": "live_scan",
                    "brand_name": brand_name,
                    "domain": _url_domain,
                }, on_conflict="workspace_id, brand_name, prompt_text")
                p_resp = await asyncio.to_thread(p_insert.execute)
                prompts_cache[q] = p_resp.data[0]["id"]
            
            async def run_single(query_text, prompt_id, engine_str, pass_number, scan_group_id):
                try:
                    # Smart Engine Mapper
                    n = engine_str.lower().strip()
                    mapping = {
                        "chatgpt": "openai", "gpt": "openai", "gpt-4": "openai", "gpt4": "openai", 
                        "openai": "openai",
                        "anthropic": "claude", "claude": "claude", "claude3": "claude", "claude-3": "claude",
                        "gemini": "gemini", "google": "gemini", "bard": "gemini",
                        "perplexity": "perplexity", "sonar": "perplexity",
                        "deepseek": "deepseek", "groq": "groq", "grok": "grok", "xai": "grok"
                    }
                    mapped_eng_str = mapping.get(n, n)
                    
                    eng = EngineType(mapped_eng_str)
                    provider = get_provider(eng)
                    if hasattr(provider, "__aenter__"):
                        async with provider as p:
                            res = await p.query(query_text, location=location)
                    else:
                        res = await provider.query(query_text, location=location)
                    
                    try:
                        from app.services.citations import reconcile_citations, is_valid_url
                        # Only skip judge citation extraction if native citations are
                        # actually valid — not merely present (Issue 12: otherwise a
                        # run with all-invalid native URLs ends up with zero citations,
                        # since the judge was never asked to extract any).
                        has_native = any(is_valid_url(c.get("url", "")) for c in (res.native_citations or []))
                        ext = await extract_mentions_and_citations(res.raw_text, brand_name, skip_citations=has_native)
                        ext.citations = reconcile_citations(res, ext.citations, f"mcp_scan_{scan_group_id}")
                    except Exception as je:
                        judge_error_msg = "Timeout" if isinstance(je, (asyncio.TimeoutError, TimeoutError)) else str(je)
                        r_insert = db.table("aeo_runs").insert({
                            "workspace_id": workspace_id,
                            "prompt_id": prompt_id,
                            "engine": mapped_eng_str,
                            "iso_week": iso_week,
                            "status": "judge_failed",
                            "error_message": judge_error_msg,
                            "raw_response": res.raw_text,
                            "cost_usd": 0.001,
                            "pass_number": pass_number,
                            "scan_group_id": scan_group_id
                        })
                        await asyncio.to_thread(r_insert.execute)
                        return {
                            "query": query_text,
                            "engine": mapped_eng_str,
                            "judge_failed": judge_error_msg,
                            "raw_text": res.raw_text,
                            "pass_number": pass_number,
                            "scan_group_id": scan_group_id
                        }
                    
                    # Immediate DB Write (Success)
                    r_insert = db.table("aeo_runs").insert({
                        "workspace_id": workspace_id,
                        "prompt_id": prompt_id,
                        "engine": mapped_eng_str,
                        "iso_week": iso_week,
                        "status": "complete",
                        "raw_response": res.raw_text,
                        "cost_usd": 0.001,
                        "pass_number": pass_number,
                        "scan_group_id": scan_group_id
                    })
                    r_resp = await asyncio.to_thread(r_insert.execute)
                    
                    if r_resp.data:
                        run_id = r_resp.data[0]["id"]
                        
                        mentions_to_insert = []
                        for m in ext.mentions:
                            m_name = m.brand_name or ""
                            canonical_m, b_id = await normalize(m_name, str(workspace_id), db, brand_cache=brand_cache)

                            target_lower = canonical_brand_name.lower()
                            m_lower = canonical_m.lower()
                            is_target = (
                                m.is_target_brand
                                or target_lower in m_lower
                                or m_lower in target_lower
                                or m_lower.startswith(target_lower)
                                or target_lower.startswith(m_lower)
                            )
                                
                            mentions_to_insert.append({
                                "workspace_id": workspace_id,
                                "run_id": run_id,
                                "raw_name": m_name,
                                "brand_name": canonical_m,
                                "brand_id": b_id,
                                "is_target_brand": is_target,
                                "position": m.position
                            })
                        if mentions_to_insert:
                            m_insert = db.table("aeo_mentions").insert(mentions_to_insert)
                            await asyncio.to_thread(m_insert.execute)
                            
                        citations_to_insert = []
                        for c in ext.citations:
                            if c.url:
                                citations_to_insert.append({
                                    "workspace_id": workspace_id,
                                    "run_id": run_id,
                                    "url": c.url,
                                    "domain": c.domain,
                                    "source": c.source or "judge_extracted"
                                })
                        if citations_to_insert:
                            c_insert = db.table("aeo_citations").insert(citations_to_insert)
                            await asyncio.to_thread(c_insert.execute)

                    return {
                        "query": query_text,
                        "engine": mapped_eng_str,
                        "mentions": [m.dict() for m in ext.mentions],
                        "citations": [c.dict() for c in ext.citations],
                        "raw_text": res.raw_text,
                        "pass_number": pass_number,
                        "scan_group_id": scan_group_id
                    }
                except Exception as e:
                    error_msg = "Timeout" if isinstance(e, (asyncio.TimeoutError, TimeoutError)) else str(e)
                    r_insert = db.table("aeo_runs").insert({
                        "workspace_id": workspace_id,
                        "prompt_id": prompt_id,
                        "engine": engine_str,
                        "iso_week": iso_week,
                        "status": "error",
                        "error_message": error_msg,
                        "cost_usd": 0.001,
                        "pass_number": pass_number,
                        "scan_group_id": scan_group_id
                    })
                    await asyncio.to_thread(r_insert.execute)
                    return {"query": query_text, "engine": engine_str, "error": error_msg, "pass_number": pass_number, "scan_group_id": scan_group_id}
            
            tasks = []
            for q in suggested_queries:
                for m in models:
                    scan_group_id = str(uuid.uuid4())
                    for p_num in range(1, passes + 1):
                        tasks.append(run_single(q, prompts_cache[q], m, p_num, scan_group_id))
            
            # Overall scan timeout: return partial results rather than hanging past the
            # aeo-job-runner 240s ceiling. 200s gives us 40s headroom for DB writes + overhead.
            SCAN_TIMEOUT = 200
            try:
                results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=SCAN_TIMEOUT)
                # Unwrap exceptions returned by return_exceptions=True
                results = [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]
            except asyncio.TimeoutError:
                logger.warning("Scan timed out after %ds — returning partial results.", SCAN_TIMEOUT)
                # Collect whatever finished; mark the rest as timeout errors
                results = []
                timed_out = True
            else:
                timed_out = False
            
            # Structured JSON response (Scan Report card — see AEO_CARD_CONTRACTS.md
            # §"Scan Report card"), replacing the old hand-formatted markdown string.
            # Per the card contract's own rule #1, a non-JSON response can never
            # render as a real card or carry buttons — this is the root reason the
            # per-topic view previously looked flat no matter what the renderer did.
            grouped_results = defaultdict(list)
            for res in results:
                if res and res.get('query'):
                    grouped_results[res.get('query')].append(res)

            if grouped_results:
                first_query = list(grouped_results.keys())[0]
                LAST_SEARCHED_TOPICS[str(workspace_id)] = first_query
                all_citations = []
                for res in grouped_results[first_query]:
                    for c in res.get('citations', []):
                        if c.get('url'):
                            all_citations.append(c.get('url'))
                LAST_SEARCHED_CITATIONS[str(workspace_id)] = list(set(all_citations))

            topics_payload = []
            for query, engine_results in grouped_results.items():
                engine_groups = defaultdict(list)
                for res in engine_results:
                    engine_groups[res.get('engine', 'Unknown').title()].append(res)

                engines_hit = []      # [{"name": ..., "position": ...}]
                engines_missed = []   # [name, ...] — explicitly named, not just a fraction
                brand_tally = {}
                sample_losing_answer = None

                for engine_name, res_list in engine_groups.items():
                    successful_passes = [r for r in res_list if "error" not in r]
                    if not successful_passes:
                        engines_missed.append(engine_name)
                        continue

                    target_mentions = 0
                    pos_list = []
                    for res in successful_passes:
                        mentions = res.get('mentions', [])
                        target_mention = next((m for m in mentions if m.get('is_target_brand')), None)
                        if target_mention:
                            target_mentions += 1
                            if target_mention.get('position'):
                                pos_list.append(target_mention.get('position'))
                        else:
                            sample_losing_answer = sample_losing_answer or res.get('raw_text')

                        for m in mentions:
                            c_name = m.get('brand_name', 'Unknown')
                            if c_name:
                                brand_tally[c_name] = brand_tally.get(c_name, 0) + 1

                    mention_rate = target_mentions / len(successful_passes)
                    if mention_rate >= 0.5:
                        engines_hit.append({"name": engine_name, "position": (pos_list[0] if pos_list else None)})
                    else:
                        engines_missed.append(engine_name)

                total_engines = len(engine_groups)
                win_count = len(engines_hit)
                visibility_pct = int(round((win_count / total_engines) * 100)) if total_engines else 0

                winners = []
                if brand_tally:
                    sorted_brands = sorted(brand_tally.items(), key=lambda x: (-x[1], x[0]))
                    winners = [c[0] for c in sorted_brands[:3]]

                gap = None
                if engines_missed and sample_losing_answer:
                    gap = await _generate_topic_gap(query, brand_name, winners, sample_losing_answer)

                if engines_hit:
                    summary = f"{win_count}/{total_engines} engines cite {brand_name} for this topic."
                else:
                    summary = f"Not cited by any of {total_engines} engines checked for this topic."

                topics_payload.append({
                    "topic": query,
                    "visibility": visibility_pct,
                    "engines_hit": engines_hit,
                    "engines_missed": engines_missed,
                    "winners": winners,
                    "gap": gap,
                    "summary": summary,
                })

            failed_runs = [r for r in results if r and ("error" in r)]
            failed_payload = None
            if failed_runs:
                failed_engines = sorted(set([r.get("engine", "Unknown").title() for r in failed_runs]))
                failed_payload = {
                    "count": len(failed_runs),
                    "total": len([r for r in results if r]),
                    "engines": failed_engines,
                }

            payload = {
                "brand": brand_name,
                "location": location or "Global",
                "active_engines": [m.title() for m in models],
                "skipped_engines": [s.title() for s in skipped] if skipped else [],
                "timed_out": timed_out,
                "failed": failed_payload,
                "topics": topics_payload,
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_content_gaps":
            topic = arguments.get("topic")
            
            # State-memory fallback
            if not topic:
                topic = LAST_SEARCHED_TOPICS.get(str(workspace_id))
                if not topic and active_prompt_ids:
                    # Robust fallback to database if memory was cleared by server restart
                    # (brand-scoped — otherwise this could pick another brand's last topic)
                    recent = await asyncio.to_thread(lambda: db.table("aeo_runs").select("created_at, aeo_prompts(prompt_text)").eq("workspace_id", workspace_id).in_("prompt_id", active_prompt_ids).order("created_at", desc=True).limit(1).execute())
                    if recent.data and recent.data[0].get("aeo_prompts"):
                        topic = recent.data[0]["aeo_prompts"].get("prompt_text")

                if not topic:
                    return [types.TextContent(type="text", text="I couldn't determine which topic you want to analyze for content gaps. Could you tell me what specific topic or query you'd like to rank higher for? Alternatively, I can run a fresh live scan first.")]

            urls = []
            # First try DB (brand-scoped — never pull another brand's cited URLs)
            if active_prompt_ids:
                prompt_data = await asyncio.to_thread(lambda: db.table("aeo_prompts").select("id").eq("workspace_id", workspace_id).in_("id", active_prompt_ids).ilike("prompt_text", f"%{topic}%").limit(1).execute())
                if prompt_data.data:
                    prompt_id = prompt_data.data[0]["id"]
                    runs = await asyncio.to_thread(lambda: db.table("aeo_runs").select("id").eq("prompt_id", prompt_id).execute())
                    if runs.data:
                        run_ids = [r["id"] for r in runs.data]
                        citations = chunked_in_fetch(db, "aeo_citations", "url", workspace_id, "run_id", run_ids)
                        urls = list(set([c["url"] for c in citations if c["url"]]))[:10]

            # Fallback to live cache if not in DB
            if not urls and topic == LAST_SEARCHED_TOPICS.get(str(workspace_id)):
                urls = LAST_SEARCHED_CITATIONS.get(str(workspace_id), [])

            if not urls:
                return [types.TextContent(type="text", text=f"No competitor URLs have been cited for this topic yet.")]

            brand = active_brand_name or "Your Brand"

            from app.services.content_analyzer import analyze_content_gaps
            strategy = await analyze_content_gaps(urls, topic, brand)
            
            return [types.TextContent(type="text", text=strategy)]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.exception(f"MCP Tool '{name}' error: {e}")
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
            return [types.TextContent(type="text", text=f"AI provider rate limit hit during '{name}'. All fallback providers were also unavailable. Please wait a moment and retry, or check your API key quotas.")]
        return [types.TextContent(type="text", text=f"Tool '{name}' failed: {str(e)}")]

# FastAPI Router integration
router = APIRouter()
sse = SseServerTransport("/mcp/messages")

@router.get("/mcp")
async def handle_sse(request: Request):
    """MCP SSE endpoint."""
    from app.config import get_settings
    settings = get_settings()
    import secrets
    
    # Allow either X-API-Key (Slack bot) or Authorization: Bearer (Lovable)
    is_authorized = False
    
    api_key = request.headers.get("X-API-Key")
    if api_key and settings.MCP_API_KEY and secrets.compare_digest(api_key, settings.MCP_API_KEY):
        is_authorized = True
        
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]
        if settings.MCP_AUTH_TOKEN and secrets.compare_digest(token, settings.MCP_AUTH_TOKEN):
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")
            
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )

@router.post("/mcp/messages")
async def handle_messages(request: Request):
    """MCP POST messages endpoint."""
    from app.config import get_settings
    settings = get_settings()
    import secrets
    
    is_authorized = False
    
    api_key = request.headers.get("X-API-Key")
    if api_key and settings.MCP_API_KEY and secrets.compare_digest(api_key, settings.MCP_API_KEY):
        is_authorized = True
        
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]
        if settings.MCP_AUTH_TOKEN and secrets.compare_digest(token, settings.MCP_AUTH_TOKEN):
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")
            
    await sse.handle_post_message(request.scope, request.receive, request._send)
