import asyncio
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("backend/.env")

from app.database import get_supabase
db = get_supabase()
from app.services.discovery import run_discovery
from app.services.providers.base import get_provider, EngineType
from app.services.judge import extract_mentions_and_citations

async def main():
    url = "netflix.com"
    location = "India"
    queries_count = 2
    models = ["openai", "perplexity"]
    passes = 3
    
    ws_res = db.table("workspaces").select("id").limit(1).execute()
    workspace_id = ws_res.data[0]["id"]
    
    t0 = time.time()
    print(f"[INSTRUMENT] t0: Scan start")
    
    discovery = await run_discovery(url, num_queries=queries_count)
    brand_name = discovery.get("brand_name", url)
    suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])][:queries_count]
    
    t1 = time.time()
    print(f"[INSTRUMENT] t1: Discovery complete - {(t1-t0):.2f}s")
    
    async def run_single(query_text, engine_str, pass_number, scan_group_id):
        t_task_start = time.time()
        engine_time = 0
        judge_time = 0
        try:
            n = engine_str.lower().strip()
            mapping = {
                "openai": "openai",
                "perplexity": "perplexity"
            }
            mapped_eng_str = mapping.get(n, n)
            eng = EngineType(mapped_eng_str)
            provider = get_provider(eng)
            
            t_eng_start = time.time()
            if hasattr(provider, "__aenter__"):
                async with provider as p:
                    res = await p.query(query_text, location=location)
            else:
                res = await provider.query(query_text, location=location)
            engine_time = time.time() - t_eng_start
            
            try:
                t_judge_start = time.time()
                from app.services.citations import reconcile_citations
                has_native = bool(res.native_citations)
                ext = await extract_mentions_and_citations(res.raw_text, brand_name, skip_citations=has_native)
                ext.citations = reconcile_citations(res, ext.citations, f"mcp_scan_{scan_group_id}")
                judge_time = time.time() - t_judge_start
            except Exception as je:
                judge_error_msg = str(je)
                return {"query": query_text, "engine": mapped_eng_str, "judge_failed": judge_error_msg, "engine_time": engine_time, "judge_time": judge_time}
                
            return {"query": query_text, "engine": mapped_eng_str, "engine_time": engine_time, "judge_time": judge_time}
        except Exception as e:
            return {"query": query_text, "engine": engine_str, "error": str(e), "engine_time": engine_time, "judge_time": 0}

    tasks = []
    for q in suggested_queries:
        for m in models:
            scan_group_id = str(uuid.uuid4())
            for p_num in range(1, passes + 1):
                tasks.append(run_single(q, m, p_num, scan_group_id))
    
    results = await asyncio.gather(*tasks)
    
    t2 = time.time()
    t3 = time.time()
    print(f"[INSTRUMENT] t2 & t3: Engine & Judge calls complete - {(t2-t1):.2f}s (Total: {(t2-t0):.2f}s)")
    
    stats = {}
    for r in results:
        eng = r.get("engine", "Unknown")
        if eng not in stats:
            stats[eng] = {"count": 0, "failures": 0, "engine_times": [], "judge_times": []}
        stats[eng]["count"] += 1
        if "error" in r or "judge_failed" in r:
            stats[eng]["failures"] += 1
        if r.get("engine_time"):
            stats[eng]["engine_times"].append(r["engine_time"])
        if r.get("judge_time"):
            stats[eng]["judge_times"].append(r["judge_time"])
            
    for eng, s in stats.items():
        avg_eng = sum(s["engine_times"]) / max(1, len(s["engine_times"]))
        avg_judge = sum(s["judge_times"]) / max(1, len(s["judge_times"]))
        print(f"[INSTRUMENT] Provider: {eng} | Calls: {s['count']} | Failures: {s['failures']} | Avg Engine Resp: {avg_eng:.2f}s | Avg Judge Resp: {avg_judge:.2f}s")
        
    t4 = time.time()
    print(f"[INSTRUMENT] t4: DB writes complete (mocked) - 0.00s (Total: {(t4-t0):.2f}s)")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
