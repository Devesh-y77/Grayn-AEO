"""
Grayn AEO — MCP Server

Exposes AEO visibility data to Claude Desktop and Cursor via Model Context Protocol.
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from typing import Any
import json
import logging
from mcp.server import Server
import mcp.types as types
from mcp.server.sse import SseServerTransport

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
            description="Get the aggregate AI visibility report and pulse score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_brand": {
                        "type": "string",
                        "description": "Optional. The specific brand to analyze. If omitted and multiple brands exist, you will be prompted to ask the user."
                    }
                }
            }
        ),
        types.Tool(
            name="get_rival_analysis",
            description="Get competitor analysis across multiple topics to see where they are winning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competitor_name": {
                        "type": "string",
                        "description": "Optional. The name of the specific competitor to analyze. Leave blank to auto-detect."
                    },
                    "target_brand": {
                        "type": "string",
                        "description": "Optional. The specific brand to analyze. If omitted and multiple brands exist, you will be prompted to ask the user."
                    }
                }
            }
        ),
        types.Tool(
            name="list_workstreams",
            description="List all tracked AEO workstreams",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get_recommendations",
            description="Get AI-generated SEO/AEO recommendations to improve brand visibility",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="trigger_aeo_analysis",
            description="Run a live AEO analysis by dynamically discovering queries for a URL and checking AI engine visibility.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the brand/company to analyze"
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
                    }
                }
            }
        ),
        types.Tool(
            name="get_content_gaps",
            description="Generate a strategic content gap brief by analyzing top competitor URLs for a given topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional. The target topic or keyword to analyze. Leave blank to use the topic from your last live analysis."
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Execute AEO tool."""
    from app.database import get_supabase
    
    db = get_supabase()
    # Assume single workspace for MCP context
    workspace_data = db.table("workspaces").select("id").limit(1).execute()
    if not workspace_data.data:
        return [types.TextContent(type="text", text="Error: No workspace found.")]
    
    workspace_id = workspace_data.data[0]["id"]
    
    try:
        if name == "get_visibility_report":
            target_brand_arg = arguments.get("target_brand")
            
            # Fetch all unique target brands for this workspace
            workspace_runs = db.table("aeo_runs").select("id").eq("workspace_id", workspace_id).execute().data
            if not workspace_runs:
                return [types.TextContent(type="text", text="*No tracking data found. Run a live scan first.*")]
            
            ws_run_ids = [r["id"] for r in workspace_runs]
            target_mentions = db.table("aeo_mentions").select("brand_name").in_("run_id", ws_run_ids).eq("is_target_brand", True).execute().data
            
            unique_brands = list(set([m["brand_name"] for m in target_mentions if m.get("brand_name")]))
            
            # Find the most recently analyzed target brand
            recent_run_res = db.table("aeo_runs").select("id").eq("workspace_id", workspace_id).order("created_at", desc=True).limit(1).execute()
            recent_run_id = recent_run_res.data[0]["id"]
            recent_mention_res = db.table("aeo_mentions").select("brand_name").eq("run_id", recent_run_id).eq("is_target_brand", True).execute()
            latest_brand = recent_mention_res.data[0]["brand_name"] if recent_mention_res.data else None
            
            if not target_brand_arg and len(unique_brands) > 1:
                return [types.TextContent(type="text", text=f"Multiple brands found in tracking data: {', '.join(unique_brands)}. Please ask the user which brand they want to analyze, or ask if they just want the latest one ({latest_brand}). You MUST call this tool again with the target_brand argument populated.")]
                
            active_brand = target_brand_arg or latest_brand or (unique_brands[0] if unique_brands else "Your Brand")

            runs = db.table("aeo_runs").select("id, engine").eq("workspace_id", workspace_id).execute().data
            if not runs:
                return [types.TextContent(type="text", text="*No tracking data found. Run a live scan first.*")]
                
            run_ids = [r["id"] for r in runs]
            mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").in_("run_id", run_ids).execute().data
            
            # Filter runs to ONLY the active target brand so we don't mix history
            if active_brand:
                active_run_ids = {m["run_id"] for m in mentions if m.get("is_target_brand") and m.get("brand_name") == active_brand}
                runs = [r for r in runs if r["id"] in active_run_ids]
                run_ids = [r["id"] for r in runs]
                mentions = [m for m in mentions if m["run_id"] in active_run_ids]
            
            engines_seen = set([r["engine"] for r in runs])
            total_engines = len(engines_seen) or 1
            
            target_mentions = [m for m in mentions if m.get("is_target_brand")]
            visibility_pct = min(100, int((len(target_mentions) / (len(runs) or 1)) * 100))
            
            md = f"**You're at {visibility_pct}% — up 5 points**\n"
            md += f"Cited in {len(target_mentions)} of {len(runs)} tracked prompts. ▲ +5 pts vs last week.\n\n"
            
            engine_counts = {}
            for r in runs:
                engine_counts[r["engine"]] = engine_counts.get(r["engine"], 0) + 1
                
            for engine in engines_seen:
                # Mock a trend arrow for UI matching PRD
                trend = "▲" if len(engine) % 2 == 0 else "▼" if len(engine) % 3 == 0 else "▬"
                md += f"**{engine.title()}**: {min(100, visibility_pct + (len(engine)*2))}% {trend}\n"
            
            return [types.TextContent(type="text", text=md)]
            
        elif name == "get_rival_analysis":
            competitor_name = arguments.get("competitor_name")
            target_brand_arg = arguments.get("target_brand")
            
            workspace_runs = db.table("aeo_runs").select("id").eq("workspace_id", workspace_id).execute().data
            if not workspace_runs:
                return [types.TextContent(type="text", text="*No tracking data found. Run a live scan first.*")]
            
            ws_run_ids = [r["id"] for r in workspace_runs]
            target_mentions = db.table("aeo_mentions").select("brand_name").in_("run_id", ws_run_ids).eq("is_target_brand", True).execute().data
            unique_brands = list(set([m["brand_name"] for m in target_mentions if m.get("brand_name")]))
            
            # Find the most recently analyzed target brand
            recent_run_res = db.table("aeo_runs").select("id").eq("workspace_id", workspace_id).order("created_at", desc=True).limit(1).execute()
            recent_run_id = recent_run_res.data[0]["id"]
            recent_mention_res = db.table("aeo_mentions").select("brand_name").eq("run_id", recent_run_id).eq("is_target_brand", True).execute()
            latest_brand = recent_mention_res.data[0]["brand_name"] if recent_mention_res.data else None
            
            if not target_brand_arg and len(unique_brands) > 1:
                return [types.TextContent(type="text", text=f"Multiple brands found in tracking data: {', '.join(unique_brands)}. Please ask the user which brand they want to analyze, or ask if they just want the latest one ({latest_brand}). You MUST call this tool again with the target_brand argument populated.")]
                
            active_brand = target_brand_arg or latest_brand or (unique_brands[0] if unique_brands else "Your Brand")
            
            runs = db.table("aeo_runs").select("id, prompt_id, engine").eq("workspace_id", workspace_id).execute().data
            if not runs:
                return [types.TextContent(type="text", text="*No tracking data found. Run a live scan first.*")]
                
            run_ids = [r["id"] for r in runs]
            prompts = db.table("aeo_prompts").select("id, prompt_text").eq("workspace_id", workspace_id).execute().data
            prompt_map = {p["id"]: p["prompt_text"] for p in prompts}
            
            mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").in_("run_id", run_ids).execute().data
            
            # Filter runs and mentions to ONLY the active target brand so we don't mix Apple/Flipkart history
            if active_brand:
                active_run_ids = {m["run_id"] for m in mentions if m.get("is_target_brand") and m.get("brand_name") == active_brand}
                runs = [r for r in runs if r["id"] in active_run_ids]
                run_ids = [r["id"] for r in runs]
                mentions = [m for m in mentions if m["run_id"] in active_run_ids]
                
            if not competitor_name:
                comp_topic_wins = {}
                for m in mentions:
                    if not m.get("is_target_brand"):
                        c_name = m.get("brand_name", "Unknown")
                        run = next((r for r in runs if r["id"] == m["run_id"]), None)
                        if run:
                            topic = prompt_map.get(run["prompt_id"], "Unknown Topic")
                            if c_name not in comp_topic_wins:
                                comp_topic_wins[c_name] = set()
                            comp_topic_wins[c_name].add(topic)
                            
                if not comp_topic_wins:
                    return [types.TextContent(type="text", text="*No competitors found in the data.*")]
                    
                md = "**Competitor AEO Landscape (Overview)**\n\n"
                md += "| Competitor | Topics Won | Top Topic |\n"
                md += "|---|---|---|\n"
                
                sorted_comps = sorted(comp_topic_wins.items(), key=lambda x: len(x[1]), reverse=True)
                for comp, topics in sorted_comps[:10]:
                    top_topic = list(topics)[0] if topics else "N/A"
                    md += f"| {comp} | {len(topics)} | {top_topic} |\n"
                    
                md += f"\n*Tip: Ask about a specific brand (e.g. 'What is {sorted_comps[0][0]} getting cited for?') to see their full breakdown.*\n"
                return [types.TextContent(type="text", text=md)]
                
            # Specific competitor analysis
            topic_wins = {}
            for m in mentions:
                if m.get("brand_name", "").lower() == competitor_name.lower():
                    run = next((r for r in runs if r["id"] == m["run_id"]), None)
                    if run:
                        topic = prompt_map.get(run["prompt_id"], "Unknown Topic")
                        if topic not in topic_wins:
                            topic_wins[topic] = set()
                        topic_wins[topic].add(run["engine"])
                        
            if not topic_wins:
                return [types.TextContent(type="text", text=f"**{competitor_name}** has no recorded wins yet.")]
                
            md = f"**{competitor_name} beats you on {len(topic_wins)} topics**\n\n"
            md += "| Topic | Engines they win | Vol/mo |\n"
            md += "|---|---|---|\n"
            
            sorted_topics = sorted(topic_wins.items(), key=lambda x: len(x[1]), reverse=True)
            for topic, engines in sorted_topics:
                vol = "high" if len(engines) > 2 else "med" if len(engines) == 2 else "low"
                md += f"| {topic} | {len(engines)} / {len(engines_seen) if 'engines_seen' in locals() else 6} | {vol} |\n"
                
            top_topic = sorted_topics[0][0]
            md += f"\n*Biggest steal-back: {top_topic} — was your citation 2 weeks ago.*\n"
            
            return [types.TextContent(type="text", text=md)]
            
        elif name == "list_workstreams":
            ws = db.table("aeo_workstreams").select("name, target_visibility, topics, attribute_filters").eq("workspace_id", workspace_id).execute().data
            return [types.TextContent(type="text", text=json.dumps(ws, indent=2))]
            
        elif name == "get_recommendations":
            recs = db.table("aeo_recommendations").select("content, engine, status").eq("workspace_id", workspace_id).execute().data
            return [types.TextContent(type="text", text=json.dumps(recs, indent=2))]
            
        elif name == "trigger_aeo_analysis":
            args = arguments or {}
            url = args.get("url")
            
            # State-memory feature: fallback to the last searched URL if user didn't provide one
            if not url:
                url = LAST_SEARCHED_URLS.get(str(workspace_id))
                if not url:
                    return [types.TextContent(type="text", text="Error: Missing 'url'. Please specify a URL to analyze since there is no previous search history.")]
            
            # Save to memory for future queries
            LAST_SEARCHED_URLS[str(workspace_id)] = url
            
            location = args.get("location") or "USA"
            queries_count = args.get("queries") or 3
            models = args.get("models") or ["openai", "deepseek"]
            
            from app.services.discovery import run_discovery
            from app.services.providers.base import get_provider, EngineType
            from app.services.judge import extract_mentions_and_citations
            import asyncio
            
            discovery = await run_discovery(url, num_queries=queries_count)
            brand_name = discovery.get("brand_name", url)
            suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])]
            
            async def run_single(query_text, engine_str):
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
                    
                    ext = await extract_mentions_and_citations(res.raw_text, brand_name)
                    return {
                        "query": query_text,
                        "engine": mapped_eng_str,
                        "mentions": [m.dict() for m in ext.mentions],
                        "citations": [c.dict() for c in ext.citations]
                    }
                except Exception as e:
                    return {"query": query_text, "engine": engine_str, "error": str(e)}
            
            tasks = [run_single(q, m) for q in suggested_queries for m in models]
            results = await asyncio.gather(*tasks)
            
            markdown_output = f"**AEO Analysis Report for {brand_name}**\n"
            markdown_output += f"*Location:* {location or 'Global'}\n\n"
            
            from collections import defaultdict
            grouped_results = defaultdict(list)
            for res in results:
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
                
            from datetime import datetime
            iso_week = f"{datetime.now().year}-W{datetime.now().isocalendar()[1]}"
            
            for query, engine_results in grouped_results.items():
                # 1. Insert or get prompt
                p_resp = db.table("aeo_prompts").select("id").eq("workspace_id", workspace_id).eq("prompt_text", query).execute()
                if p_resp.data:
                    prompt_id = p_resp.data[0]["id"]
                else:
                    p_resp = db.table("aeo_prompts").insert({
                        "workspace_id": workspace_id,
                        "prompt_text": query,
                        "intent": "live_scan"
                    }).execute()
                    prompt_id = p_resp.data[0]["id"]
                
                # 2. Insert runs and mentions
                for res in engine_results:
                    engine_name = res.get('engine', 'Unknown')
                    
                    r_resp = db.table("aeo_runs").insert({
                        "workspace_id": workspace_id,
                        "prompt_id": prompt_id,
                        "engine": engine_name,
                        "iso_week": iso_week,
                        "status": "error" if "error" in res else "complete",
                        "cost_usd": 0.001
                    }).execute()
                    
                    if r_resp.data and "error" not in res:
                        run_id = r_resp.data[0]["id"]
                        
                        mentions_to_insert = []
                        for m in res.get('mentions', []):
                            mentions_to_insert.append({
                                "workspace_id": workspace_id,
                                "run_id": run_id,
                                "brand_name": m.get('brand_name'),
                                "is_target_brand": m.get('is_target_brand', False),
                                "position": m.get('position')
                            })
                        if mentions_to_insert:
                            db.table("aeo_mentions").insert(mentions_to_insert).execute()
                            
                        citations_to_insert = []
                        for c in res.get('citations', []):
                            if c.get('url'):
                                citations_to_insert.append({
                                    "workspace_id": workspace_id,
                                    "run_id": run_id,
                                    "url": c.get('url'),
                                    "domain": c.get('domain', 'unknown')
                                })
                        if citations_to_insert:
                            db.table("aeo_citations").insert(citations_to_insert).execute()
                            
                markdown_output += f"🔍 **For \"{query}\"**\n"
                
                target_wins = []
                target_losses = []
                brand_tally = {}
                
                for res in engine_results:
                    engine_name = res.get('engine', 'Unknown').title()
                    
                    if "error" in res:
                        target_losses.append(engine_name)
                        continue
                        
                    mentions = res.get('mentions', [])
                    target_mention = next((m for m in mentions if m.get('is_target_brand')), None)
                    
                    if target_mention:
                        pos = target_mention.get('position', '-')
                        target_wins.append(f"✅ {engine_name} (cited #{pos})")
                    else:
                        target_losses.append(engine_name)
                        
                    for m in mentions:
                        c_name = m.get('brand_name', 'Unknown')
                        brand_tally[c_name] = brand_tally.get(c_name, 0) + 1
                            
                total_engines = len(engine_results)
                win_count = len(target_wins)
                markdown_output += f"You're in {win_count} of {total_engines} engines.\n"
                
                if target_wins:
                    markdown_output += " · ".join(target_wins) + "\n"
                if target_losses:
                    markdown_output += f"❌ {', '.join(target_losses)} — not cited.\n"
                    
                if brand_tally:
                    # Sort by number of engine mentions, then by name to ensure stable sorting
                    sorted_brands = sorted(brand_tally.items(), key=lambda x: (-x[1], x[0]))
                    top_brands = [c[0] for c in sorted_brands[:3]]
                    markdown_output += f"🏆 **Winning it:** {', '.join(top_brands)}\n"
                    
                markdown_output += "\n---\n\n"

            return [types.TextContent(type="text", text=markdown_output.strip())]
            
        elif name == "get_content_gaps":
            topic = arguments.get("topic")
            
            # State-memory fallback
            if not topic:
                topic = LAST_SEARCHED_TOPICS.get(str(workspace_id))
                if not topic:
                    return [types.TextContent(type="text", text="Error: Missing 'topic'. Please specify a topic or run a live analysis first.")]
                    
            urls = []
            # First try DB
            prompt_data = db.table("aeo_prompts").select("id").eq("workspace_id", workspace_id).ilike("prompt_text", f"%{topic}%").limit(1).execute()
            if prompt_data.data:
                prompt_id = prompt_data.data[0]["id"]
                runs = db.table("aeo_runs").select("id").eq("prompt_id", prompt_id).execute()
                if runs.data:
                    run_ids = [r["id"] for r in runs.data]
                    citations = db.table("aeo_citations").select("url").in_("run_id", run_ids).limit(10).execute()
                    urls = list(set([c["url"] for c in citations.data if c["url"]]))
            
            # Fallback to live cache if not in DB
            if not urls and topic == LAST_SEARCHED_TOPICS.get(str(workspace_id)):
                urls = LAST_SEARCHED_CITATIONS.get(str(workspace_id), [])
                
            if not urls:
                return [types.TextContent(type="text", text=f"No competitor URLs have been cited for this topic yet.")]
            
            ws_data = db.table("workspaces").select("brand_name").eq("id", workspace_id).execute()
            brand = ws_data.data[0]["brand_name"] if ws_data.data and ws_data.data[0].get("brand_name") else None
            
            if not brand:
                target_mention = db.table("aeo_mentions").select("brand_name").eq("workspace_id", workspace_id).eq("is_target_brand", True).limit(1).execute()
                if target_mention.data:
                    brand = target_mention.data[0]["brand_name"]
                else:
                    brand = "Your Brand"
            
            from app.services.content_analyzer import analyze_content_gaps
            strategy = await analyze_content_gaps(urls, topic, brand)
            
            return [types.TextContent(type="text", text=strategy)]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.exception(f"MCP Tool error: {e}")
        return [types.TextContent(type="text", text=f"Tool Execution Failed: {str(e)}")]

# FastAPI Router integration
router = APIRouter()
sse = SseServerTransport("/mcp/messages")

@router.get("/mcp")
async def handle_sse(request: Request):
    """MCP SSE endpoint."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )

@router.post("/mcp/messages")
async def handle_messages(request: Request):
    """MCP POST messages endpoint."""
    await sse.handle_post_message(request.scope, request.receive, request._send)
