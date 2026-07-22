import os

file_path = "app/mcp_server.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "from app.services.discovery import run_discovery" in line and start_idx == -1:
        start_idx = i
    if "engine_groups = defaultdict(list)" in line and start_idx != -1 and i > start_idx + 100:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_code = """            from app.services.discovery import run_discovery
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
                                    "source": "native" if c.is_native else "judge"
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
            
            markdown_output = f"**AEO Analysis Report for {brand_name}**\\n"
            markdown_output += f"*Location:* {location or 'Global'}\\n\\n"
            
            failed_runs = [r for r in results if "error" in r or "judge_failed" in r]
            if failed_runs:
                failed_count = len(failed_runs)
                total_count = len(results)
                failed_engines = list(set([r.get("engine", "Unknown") for r in failed_runs]))
                markdown_output += f"⚠️ {failed_count}/{total_count} calls failed: {', '.join(failed_engines)}\\n\\n"
            
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
"""
    
    # We replace from start_idx to end_idx (exclusive)
    new_lines = lines[:start_idx] + [new_code] + lines[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Replaced successfully!")
else:
    print(f"Could not find indices: start={start_idx}, end={end_idx}")
