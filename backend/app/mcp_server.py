"""
Grayn AEO — MCP Server

Exposes AEO visibility data to Claude Desktop and Cursor via Model Context Protocol.
"""

from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from typing import Any
import json
import logging
from datetime import datetime
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
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history (e.g., the last scanned URL or brand). If you absolutely don't know it, ask the user."
                    }
                },
                "required": ["client_name"]
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
                        "description": "Optional. The name of the specific competitor to analyze. NEVER put the user's own brand name here. Leave blank for a general overview."
                    },
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="list_workstreams",
            description="List the topics (also known as queries, search terms, or workstreams) currently being tracked for the brand. Use this when the user asks what queries or topics were run or are being tracked.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history."
                    }
                },
                "required": ["client_name"]
            }
        ),
        types.Tool(
            name="get_top_citations",
            description="Get a list of the top domains and URLs that are cited most frequently by AI engines when referencing this brand. Use this when the user asks what sites or URLs they are getting cited the most off.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history."
                    }
                },
                "required": ["client_name"]
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
                    },
                    "passes": {
                        "type": "integer",
                        "description": "Optional. Number of multi-pass iterations per query/engine (default: 3)."
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
        ),
        types.Tool(
            name="analyze_topic",
            description="Deep dive into a specific topic to see which engines cite the brand and who the top competitors are.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "The name of the topic/keyword to analyze."
                    }
                },
                "required": ["topic_name"]
            }
        ),
        types.Tool(
            name="analyze_drop_root_cause",
            description="Analyze why a brand dropped in visibility for a specific topic by comparing today's AI output with 3 weeks ago.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic that experienced a drop in visibility."
                    }
                },
                "required": ["topic"]
            }
        ),
        types.Tool(
            name="get_raw_ai_answer",
            description="Fetch the exact raw text output generated by an AI engine for a specific topic, serving as proof.",
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
                        "description": "REQUIRED. The name of the client or brand the user is asking about. You MUST extract this from the conversation history."
                    }
                },
                "required": ["topic", "engine", "client_name"]
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
    # Frontend injects client_name, target_brand, brand, url, domain, workspace_ref
    client_name = (arguments.get("client_name") or arguments.get("target_brand") or arguments.get("brand")) if arguments else None
    url = (arguments.get("url") or arguments.get("domain")) if arguments else None
    # Lovable dispatcher will inject workspace_ref from prod DB
    injected_workspace_id = (arguments.get("workspace_ref") or arguments.get("workspace_id")) if arguments else None
    workspace_data = None
    
    # 1. System-injected workspace ID (most secure/accurate)
    if injected_workspace_id:
        ws_res = db.table("workspaces").select("id, brand_name, domain").eq("id", injected_workspace_id).execute()
        if ws_res.data:
            workspace_data = ws_res.data[0]
            
    # 2. Fuzzy match by client_name
    if not workspace_data and client_name:
        c_lower = client_name.lower()
        ws_res = db.table("workspaces").select("id, brand_name, domain").execute()
        if ws_res.data:
            for ws in ws_res.data:
                ws_brand = ws.get("brand_name") or ""
                ws_domain = ws.get("domain") or ""
                if (ws_brand and c_lower in ws_brand.lower()) or (ws_domain and c_lower in ws_domain.lower()) or (ws_brand and ws_brand.lower() in c_lower) or (ws_domain and ws_domain.lower() in c_lower):
                    workspace_data = ws
                    break
                    
    if not workspace_data and url:
        from urllib.parse import urlparse
        parsed_uri = urlparse(url if "://" in url else "https://" + url)
        domain = parsed_uri.netloc.replace("www.", "").lower()
        
        ws_res = db.table("workspaces").select("id, brand_name, domain").ilike("domain", f"%{domain}%").execute()
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
                
            new_ws = db.table("workspaces").insert(payload).execute()
            if new_ws.data:
                workspace_data = new_ws.data[0]
                
    if not workspace_data and client_name:
        return [types.TextContent(type="text", text=f"I couldn't find any existing tracking data for '{client_name}'. To get started, I can run a fresh live AEO scan. What is the website URL for {client_name}?")]
                    
    if not workspace_data:
        # Fallback to the workspace that was most recently run, instead of the oldest one
        run_res = db.table("aeo_runs").select("workspace_id").order("created_at", desc=True).limit(1).execute()
        if run_res.data:
            recent_ws_id = run_res.data[0]["workspace_id"]
            ws_res = db.table("workspaces").select("id, brand_name, domain").eq("id", recent_ws_id).execute()
            if ws_res.data:
                workspace_data = ws_res.data[0]
        # If no runs exist, fallback to the most recently created workspace
        if not workspace_data:
            res = db.table("workspaces").select("id, brand_name, domain").order("created_at", desc=True).limit(1).execute()
            if res.data:
                workspace_data = res.data[0]
            
    if not workspace_data:
        return [types.TextContent(type="text", text="I don't have any tracking data for this brand yet. Would you like me to run a fresh live analysis? If so, please provide the website URL you'd like me to scan.")]
    
    workspace_id = workspace_data["id"]
    try:
        if name == "get_visibility_report":
            from app.services.scoring import compute_visibility
            vis = compute_visibility(db, workspace_id)
            
            if not vis.iso_week:
                return [types.TextContent(type="text", text=json.dumps({"error": "No recent tracking scans found."}))]
                
            # Find the highlight: which engine grew the most?
            highlight = "No significant changes this week."
            
            from datetime import date as _date, timedelta
            year, week_num = int(vis.iso_week[:4]), int(vis.iso_week.split("W")[1])
            d = _date.fromisocalendar(year, week_num, 1) - timedelta(days=7)
            prev_week = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
                
            prev_vis = compute_visibility(db, workspace_id, prev_week)
                
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
                    
            brand_display = workspace_data.get("brand_name", "").title()
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
                "engines": []
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
                
            runs = db.table("aeo_runs").select("id, engine, scan_group_id, status, aeo_prompts!inner(prompt_text)").eq("workspace_id", workspace_id).order("created_at", desc=True).limit(200).execute().data
            if not runs:
                return [types.TextContent(type="text", text=json.dumps({"error": "No recent runs found"}))]
                
            topic_runs = [r for r in runs if r.get("aeo_prompts") and r["aeo_prompts"].get("prompt_text", "").lower() == topic_name.lower()]
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
            
            mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").in_("run_id", run_ids).execute().data
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
                
            for eng, e_runs in engine_runs.items():
                rate, groups, _ = compute_group_metrics(e_runs, mentioned_run_ids)
                engines_won.append({
                    "engine": eng.title().replace("_", " "),
                    "cited": rate > 0.5  # Consider it a win if > 50% of passes cited
                })
                
            for m in mentions:
                if not m.get("is_target_brand"):
                    c_name = m.get("brand_name", "Unknown")
                    competitor_tally[c_name] = competitor_tally.get(c_name, 0) + 1
                
            sorted_comps = sorted(competitor_tally.items(), key=lambda x: x[1], reverse=True)
            top_competitors = [c[0] for c in sorted_comps[:3]]
            
            total_rate, total_groups, _ = compute_group_metrics(latest_runs, mentioned_run_ids)
            visibility_pct = int((total_rate / total_groups) * 100) if total_groups else 0
            
            payload = {
                "topic": topic_name,
                "visibility": visibility_pct,
                "winners": top_competitors,
                "engines_hit": [e["engine"] for e in engines_won if e["cited"]],
                "summary": f"Analyzed on {len(engines_won)} engines."
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_rival_analysis":
            competitor_name = arguments.get("competitor_name")
            target_brand_arg = arguments.get("target_brand")
            
            runs = db.table("aeo_runs").select("id, prompt_id, engine, created_at, scan_group_id, status").eq("workspace_id", workspace_id).order("created_at", desc=True).execute().data
            if not runs:
                return [types.TextContent(type="text", text="I don't see any recent tracking scans for your brand, so I can't analyze competitors yet. Would you like me to run a live visibility scan right now?")]
                
                
            active_run_ids = set()
            if target_brand_arg:
                ws_run_ids = [r["id"] for r in runs]
                target_mentions = db.table("aeo_mentions").select("run_id").in_("run_id", ws_run_ids).eq("is_target_brand", True).eq("brand_name", target_brand_arg).execute().data
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
            prompts = db.table("aeo_prompts").select("id, prompt_text").eq("workspace_id", workspace_id).execute().data
            prompt_map = {p["id"]: p["prompt_text"] for p in prompts}
            
            mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").in_("run_id", run_ids).execute().data
            
            # Prevent AI from mistakenly passing the user's own brand as a competitor
            if competitor_name:
                ws_brand = (workspace_data.get("brand_name") or "").lower()
                ws_domain = (workspace_data.get("domain") or "").lower()
                c_lower = competitor_name.lower()
                if c_lower:
                    if (ws_brand and c_lower in ws_brand) or (ws_domain and c_lower in ws_domain) or (ws_domain and ws_domain in c_lower) or (ws_brand and ws_brand in c_lower):
                        competitor_name = None
                
            from app.services.consensus import compute_group_metrics, group_runs_by_scan_group, get_group_confidence
            
            if not competitor_name:
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
                
            # Specific competitor analysis
            c_topic_run_ids = defaultdict(set)
            for m in mentions:
                if m.get("brand_name", "").lower() == competitor_name.lower():
                    run = next((r for r in runs if r["id"] == m["run_id"]), None)
                    if run:
                        topic = prompt_map.get(run["prompt_id"], "Unknown Topic")
                        c_topic_run_ids[topic].add(run["id"])
                        
            if not c_topic_run_ids:
                return [types.TextContent(type="text", text=json.dumps({"error": f"{competitor_name} has no recorded wins yet."}))]
                
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
                    "delta": 0
                })
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "list_workstreams":
            # Fetch the most recent runs to get only recently tracked topics
            runs = db.table("aeo_runs").select("prompt_id, created_at, aeo_prompts(prompt_text)").eq("workspace_id", workspace_id).order("created_at", desc=True).limit(200).execute().data
            
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
                
            prompts = db.table("aeo_prompts").select("id").eq("workspace_id", workspace_id).ilike("prompt_text", f"%{topic}%").limit(1).execute().data
            if not prompts:
                return [types.TextContent(type="text", text=json.dumps({"error": f"No tracking data found for topic: {topic}"}))]
                
            prompt_id = prompts[0]["id"]
            runs = db.table("aeo_runs").select("id, raw_response").eq("prompt_id", prompt_id).ilike("engine", f"%{engine}%").order("created_at", desc=True).limit(1).execute().data
            
            if not runs or not runs[0].get("raw_response"):
                return [types.TextContent(type="text", text=json.dumps({"error": f"No raw AI answer found for {topic} on {engine}. It might be from an older scan before we started saving raw text!"}))]
                
            run_id = runs[0]["id"]
            raw_text = runs[0]["raw_response"]
            
            citations = db.table("aeo_citations").select("url").eq("run_id", run_id).execute().data
            citation_urls = [c["url"] for c in citations if c.get("url")] if citations else []
            
            payload = {
                "topic": topic.title(),
                "engine": engine.title(),
                "answer": raw_text,
                "sources": citation_urls
            }
            return [types.TextContent(type="text", text=json.dumps(payload))]
            
        elif name == "get_top_citations":
            # Fetch mentions where this brand was cited
            mentions = db.table("aeo_mentions").select("run_id").eq("workspace_id", workspace_id).eq("is_target_brand", True).execute().data
            if not mentions:
                return [types.TextContent(type="text", text="*No citations found because your brand hasn't been mentioned by any AI engines yet!*")]
                
            run_ids = list(set([m["run_id"] for m in mentions]))
            
            # Fetch the runs for these mentions so we can filter by the most recent scan session
            runs = db.table("aeo_runs").select("id, created_at").eq("workspace_id", workspace_id).in_("id", run_ids).order("created_at", desc=True).execute().data
            if not runs:
                return [types.TextContent(type="text", text="*No runs found for citations.*")]
                
            # Filter to only the most recent scan session (within 5 mins of latest run)
            latest_time = datetime.fromisoformat(runs[0]["created_at"].replace('Z', '+00:00'))
            recent_run_ids = [r["id"] for r in runs if (latest_time - datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))).total_seconds() < 300]
            
            # Fetch citations for those recent runs
            citations = db.table("aeo_citations").select("url, domain").in_("run_id", recent_run_ids).execute().data
            if not citations:
                return [types.TextContent(type="text", text="*No citation URLs found in the latest AI engine responses for your brand.*")]
                
            from collections import Counter
            domain_counts = Counter()
            url_counts = Counter()
            
            for c in citations:
                d = c.get("domain")
                u = c.get("url")
                if d and d != "unknown":
                    domain_counts[d] += 1
                if u:
                    url_counts[u] += 1
                    
            top_domains = domain_counts.most_common(10)
            top_urls = url_counts.most_common(10)
            
            md = "**🏆 Top Domains Citing Your Brand**\n"
            for d, count in top_domains:
                md += f"• {d} ({count} citations)\n"
                
            md += "\n**📄 Top Specific URLs**\n"
            for u, count in top_urls:
                # Truncate long URLs for readability
                display_u = u if len(u) < 60 else u[:57] + "..."
                md += f"• [{display_u}]({u}) ({count} citations)\n"
                
            return [types.TextContent(type="text", text=md.strip())]
            
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
                    return [types.TextContent(type="text", text="I need a website URL to run a live AEO analysis, but I couldn't find one in our history. Could you please provide the URL you'd like me to scan?")]
            
            # Save to memory for future queries
            LAST_SEARCHED_URLS[str(workspace_id)] = url
            
            location = args.get("location") or "USA"
            queries_count = args.get("queries") or 3
            models = args.get("models") or ["openai", "deepseek", "claude", "gemini", "perplexity", "grok"]
            passes = args.get("passes") or 3
            
            if queries_count * len(models) * passes > 200:
                return [types.TextContent(type="text", text="Cost guard limit exceeded: max 200 total API calls allowed per scan.")]
            
            from app.services.discovery import run_discovery
            from app.services.providers.base import get_provider, EngineType
            from app.services.judge import extract_mentions_and_citations
            import asyncio
            import uuid
            
            force_rediscovery = args.get("force_rediscovery", False)
            brand_name = workspace_data.get("brand_name")
            suggested_queries = []
            
            if brand_name and not force_rediscovery:
                cached_prompts = db.table("aeo_prompts").select("prompt_text").eq("workspace_id", workspace_id).eq("intent", "live_scan").limit(queries_count).execute()
                if cached_prompts.data and len(cached_prompts.data) > 0:
                    suggested_queries = [p["prompt_text"] for p in cached_prompts.data]
            
            if not suggested_queries:
                discovery = await run_discovery(url, num_queries=queries_count)
                brand_name = discovery.get("brand_name", url)
                
                try:
                    db.table("workspaces").update({"brand_name": brand_name, "domain": url}).eq("id", workspace_id).execute()
                except Exception:
                    pass
                    
                suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])]
                
            iso_week = f"{datetime.now().year}-W{datetime.now().isocalendar()[1]}"
            
            prompts_cache = {}
            for q in suggested_queries:
                p_insert = db.table("aeo_prompts").upsert({
                    "workspace_id": workspace_id,
                    "prompt_text": q,
                    "intent": "live_scan"
                }, on_conflict="workspace_id, prompt_text")
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
                        from app.services.citations import reconcile_citations
                        has_native = bool(res.native_citations)
                        ext = await extract_mentions_and_citations(res.raw_text, brand_name, skip_citations=has_native)
                        ext.citations = reconcile_citations(res, ext.citations, f"mcp_scan_{scan_group_id}")
                    except Exception as je:
                        import asyncio
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
                            from app.services.brand_normalizer import normalize
                            canonical_m, b_id = await normalize(m_name, str(workspace_id), db)
                            canonical_b, _ = await normalize(brand_name, str(workspace_id), db)
                            
                            is_target = m.is_target_brand
                            if is_target and canonical_b != canonical_m:
                                is_target = False
                            if not is_target and canonical_b == canonical_m:
                                is_target = True
                                
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
                    import asyncio
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
            
            results = await asyncio.gather(*tasks)
            
            markdown_output = f"**AEO Analysis Report for {brand_name}**\n"
            markdown_output += f"*Location:* {location or 'Global'}\n\n"
            
            failed_runs = [r for r in results if "error" in r or "judge_failed" in r]
            if failed_runs:
                failed_count = len(failed_runs)
                total_count = len(results)
                failed_engines = list(set([r.get("engine", "Unknown") for r in failed_runs]))
                markdown_output += f"⚠️ {failed_count}/{total_count} calls failed: {', '.join(failed_engines)}\n\n"
            
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
            
            for query, engine_results in grouped_results.items():
                engine_groups = defaultdict(list)
                for res in engine_results:
                    engine_groups[res.get('engine', 'Unknown').title()].append(res)
                    
                target_wins = []
                target_losses = []
                brand_tally = {}
                
                for engine_name, res_list in engine_groups.items():
                    successful_passes = [r for r in res_list if "error" not in r]
                    if not successful_passes:
                        target_losses.append(f"❌ {engine_name}")
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
                        
                        for m in mentions:
                            c_name = m.get('brand_name', 'Unknown')
                            if c_name:
                                brand_tally[c_name] = brand_tally.get(c_name, 0) + 1
                                
                    mention_rate = target_mentions / len(successful_passes)
                    if mention_rate >= 0.5:
                        pos = pos_list[0] if pos_list else '-'
                        target_wins.append(f"✅ {engine_name} (#{pos})")
                    else:
                        target_losses.append(f"❌ {engine_name}")
                        
                total_engines = len(engine_groups)
                win_count = len(target_wins)
                
                vis_str = f"*{win_count}/{total_engines} engines*"
                if target_wins:
                    vis_str += f" ({', '.join(target_wins)})"
                if target_losses:
                    vis_str += f" ({', '.join(target_losses)})"
                    
                top_brands_str = "None identified"
                if brand_tally:
                    # Sort by number of engine mentions, then by name to ensure stable sorting
                    sorted_brands = sorted(brand_tally.items(), key=lambda x: (-x[1], x[0]))
                    top_brands = [c[0] for c in sorted_brands[:3]]
                    top_brands_str = ", ".join(top_brands)
                    
                markdown_output += f"🔍 **{query}**\n"
                markdown_output += f"• **Your Visibility:** {vis_str}\n"
                markdown_output += f"• **Winning Brands:** {top_brands_str}\n\n"

            return [types.TextContent(type="text", text=markdown_output.strip())]
            
        elif name == "get_content_gaps":
            topic = arguments.get("topic")
            
            # State-memory fallback
            if not topic:
                topic = LAST_SEARCHED_TOPICS.get(str(workspace_id))
                if not topic:
                    # Robust fallback to database if memory was cleared by server restart
                    recent = db.table("aeo_runs").select("created_at, aeo_prompts(prompt_text)").eq("workspace_id", workspace_id).order("created_at", desc=True).limit(1).execute()
                    if recent.data and recent.data[0].get("aeo_prompts"):
                        topic = recent.data[0]["aeo_prompts"].get("prompt_text")
                        
                if not topic:
                    return [types.TextContent(type="text", text="I couldn't determine which topic you want to analyze for content gaps. Could you tell me what specific topic or query you'd like to rank higher for? Alternatively, I can run a fresh live scan first.")]
                    
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
    from app.config import get_settings
    settings = get_settings()
    if not settings.MCP_AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfiguration: MCP_AUTH_TOKEN not set")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Authorization header")
    import secrets
    if not secrets.compare_digest(auth_header.split("Bearer ")[1], settings.MCP_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid MCP Auth Token")
            
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
    if not settings.MCP_AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfiguration: MCP_AUTH_TOKEN not set")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Authorization header")
    import secrets
    if not secrets.compare_digest(auth_header.split("Bearer ")[1], settings.MCP_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid MCP Auth Token")
            
    await sse.handle_post_message(request.scope, request.receive, request._send)
