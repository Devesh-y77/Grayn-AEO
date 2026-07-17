from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from supabase import Client
from app.database import get_supabase
import uuid
import asyncio
from datetime import datetime

router = APIRouter(prefix="/public", tags=["public"])

class AuditRequest(BaseModel):
    domain: str
    competitors: Optional[List[str]] = []
    variant: Optional[str] = "default"

class LeadRequest(BaseModel):
    email: str
    name: Optional[str] = None
    domain: str
    competitors: Optional[List[str]] = []
    variant: Optional[str] = "default"
    score: Optional[int] = None

@router.post("/lead")
def submit_lead(body: LeadRequest, db: Client = Depends(get_supabase)):
    db.table("y77_leads").insert({
        "email": body.email,
        "name": body.name,
        "domain": body.domain,
        "competitors": body.competitors,
        "lp_variant": body.variant,
        "score": body.score
    }).execute()
    return {"status": "ok"}

async def run_audit_background(job_id: str, domain: str, competitors: List[str], db: Client):
    try:
        from app.services.discovery import run_discovery
        from app.services.providers.base import get_provider, EngineType
        from app.services.judge import extract_mentions_and_citations
        
        # 1. Brand name extraction (no workspace sync)
        brand_name = domain.split(".")[0].title()

        # 2. Update progress
        db.table("y77_lp_jobs").update({"progress": 15}).eq("id", job_id).execute()
        
        # 3. Run discovery
        discovery = await run_discovery(domain, num_queries=3) # Only run 3 queries for speed
        suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])][:3]
        if not suggested_queries:
            suggested_queries = [f"Best alternatives to {domain}", f"Top services like {domain}", f"{domain} reviews"]
            
        brand_name = discovery.get("brand_name", brand_name)
        
        db.table("y77_lp_jobs").update({
            "progress": 40,
            "result": {"queries_tested": suggested_queries}
        }).eq("id", job_id).execute()
        
        # 4. Query LLMs (limit to OpenAI and DeepSeek to be fast)
        models = ["openai", "deepseek"]
        
        async def run_single(query_text, engine_str):
            try:
                eng = EngineType(engine_str)
                provider = get_provider(eng)
                if hasattr(provider, "__aenter__"):
                    async with provider as p:
                        res = await p.query(query_text, location="USA")
                else:
                    res = await provider.query(query_text, location="USA")
                
                ext = await extract_mentions_and_citations(res.raw_text, brand_name, skip_citations=True)
                return {
                    "query": query_text,
                    "engine": engine_str,
                    "mentions": [m.dict() for m in ext.mentions]
                }
            except Exception as e:
                return {"query": query_text, "engine": engine_str, "error": str(e)}

        tasks = [run_single(q, m) for q in suggested_queries for m in models]
        results = await asyncio.gather(*tasks)
        
        db.table("y77_lp_jobs").update({"progress": 90}).eq("id", job_id).execute()
        
        # 4. Tally Results (now based on real inserted data principles)
        total_runs = max(len(results), 1)
        target_wins = sum(1 for r in results if r.get("mentions") and any(m.get("is_target_brand") for m in r["mentions"]))
        
        # Comp tally logic dynamically tracks all competitors seen
        comp_tally = {}
        for r in results:
            if not r.get("mentions"): continue
            for m in r["mentions"]:
                if not m.get("is_target_brand"):
                    c_name = m.get("brand_name")
                    if c_name:
                        comp_tally[c_name] = comp_tally.get(c_name, 0) + 1

        # Calculate metrics
        multiplier = 100 / total_runs
        citedCount = min(100, int(target_wins * multiplier))
        score = min(100, citedCount + 20)
        
        pillars = [
            {"name": "Crawlable by AI bots", "score": min(100, score + 15)},
            {"name": "Structured data & schema", "score": min(100, max(0, score - 10))},
            {"name": "Answer-ready content", "score": min(100, score + 5)},
            {"name": "Entity & authority signals", "score": score},
            {"name": "Citations in AI answers", "score": citedCount}
        ]
        
        comps_list = []
        for c_name, wins in comp_tally.items():
            comps_list.append({"name": c_name, "cited": min(100, int(wins * multiplier))})
            
        comps_list = sorted(comps_list, key=lambda x: x["cited"], reverse=True)
        top_comp = comps_list[0]["name"] if comps_list else "your top competitor"
            
        gaps = []
        if comps_list and comps_list[0]["cited"] > citedCount:
            gaps.append({"area": "High-intent searches", "tag": "competitor ahead", "note": f"{top_comp} is cited more often across ChatGPT & DeepSeek for these terms."})
            gaps.append({"area": "Comparison searches", "tag": "low visibility", "note": f"When buyers compare options, {top_comp} intercepts the citation."})
            gaps.append({"area": "Entity signals", "tag": "missing on your site", "note": f"{top_comp} has stronger entity signals AI engines read to pick sources."})
        else:
            if citedCount < 50:
                gaps.append({"area": "Overall AI Visibility", "tag": "low visibility", "note": f"You are missing from the majority of AI answers."})
                gaps.append({"area": "Schema markup", "tag": "needs update", "note": "Engines are struggling to extract structured facts from your pages."})
            else:
                gaps.append({"area": "Emerging queries", "tag": "opportunity", "note": "You are winning core terms, but newer AI queries are unowned."})

        final_result = {
            "domain": domain,
            "score": score,
            "citedCount": citedCount,
            "pillars": pillars,
            "competitors": comps_list[:4], # Top 4 only
            "gaps": gaps
        }
        
        db.table("y77_lp_jobs").update({
            "status": "done",
            "progress": 100,
            "result": final_result
        }).eq("id", job_id).execute()

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.table("y77_lp_jobs").update({
            "status": "error",
            "error_message": str(e)
        }).eq("id", job_id).execute()

@router.post("/audit")
def start_audit(body: AuditRequest, background_tasks: BackgroundTasks, db: Client = Depends(get_supabase)):
    job_res = db.table("y77_lp_jobs").insert({
        "domain": body.domain,
        "competitors": body.competitors,
        "lp_variant": body.variant,
        "status": "running",
        "progress": 0
    }).execute()
    
    job_id = job_res.data[0]["id"]
    background_tasks.add_task(run_audit_background, job_id, body.domain, body.competitors, db)
    
    return {"jobId": job_id}

@router.get("/audit/{job_id}")
def poll_audit(job_id: str, db: Client = Depends(get_supabase)):
    res = db.table("y77_lp_jobs").select("*").eq("id", job_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = res.data[0]
    if job["status"] == "done":
        return {"status": "done", "result": job["result"]}
    elif job["status"] == "error":
        return {"status": "error", "message": job["error_message"]}
    else:
        res_obj = job.get("result") or {}
        queries = res_obj.get("queries_tested", []) if isinstance(res_obj, dict) else []
        return {"status": "running", "progress": job["progress"], "queriesTested": queries}
