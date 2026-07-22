import re

with open("app/mcp_server.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add t0
content = content.replace('        elif name == "trigger_aeo_analysis":',
                          '        elif name == "trigger_aeo_analysis":\n            import time\n            t0 = time.time()\n            print(f"\\n\\n[INSTRUMENT] t0: Scan start")')

# Add t1
content = content.replace('            suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])]',
                          '            suggested_queries = [q["text"] for q in discovery.get("suggested_queries", [])]\n            t1 = time.time()\n            print(f"[INSTRUMENT] t1: Discovery complete - {(t1-t0):.2f}s")')

# In run_single, track engine and judge times
run_single_repl = '''
            async def run_single(query_text, engine_str, pass_number, scan_group_id):
                t_task_start = time.time()
                engine_time = 0
                judge_time = 0
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
                        import asyncio
                        judge_error_msg = "Timeout" if isinstance(je, (asyncio.TimeoutError, TimeoutError)) else str(je)
                        print(f"[INSTRUMENT] run_single failed at judge: {mapped_eng_str} - {judge_error_msg}")
                        return {
                            "query": query_text,
                            "engine": mapped_eng_str,
                            "judge_failed": judge_error_msg,
                            "raw_text": res.raw_text,
                            "pass_number": pass_number,
                            "scan_group_id": scan_group_id,
                            "engine_time": engine_time,
                            "judge_time": judge_time
                        }
                        
                    return {
                        "query": query_text,
                        "engine": mapped_eng_str,
                        "mentions": [m.dict() for m in ext.mentions],
                        "citations": [c.dict() for c in ext.citations],
                        "raw_text": res.raw_text,
                        "pass_number": pass_number,
                        "scan_group_id": scan_group_id,
                        "engine_time": engine_time,
                        "judge_time": judge_time
                    }
                except Exception as e:
                    import asyncio
                    error_msg = "Timeout" if isinstance(e, (asyncio.TimeoutError, TimeoutError)) else str(e)
                    print(f"[INSTRUMENT] run_single failed at engine: {engine_str} - {error_msg}")
                    return {"query": query_text, "engine": engine_str, "error": error_msg, "pass_number": pass_number, "scan_group_id": scan_group_id, "engine_time": engine_time, "judge_time": 0}
'''
content = re.sub(r'            async def run_single\(query_text, engine_str, pass_number, scan_group_id\):.*?return \{"query": query_text, "engine": engine_str, "error": error_msg, "pass_number": pass_number, "scan_group_id": scan_group_id\}', run_single_repl, content, flags=re.DOTALL)

# Add t2/t3 at gather end
content = content.replace('            results = await asyncio.gather(*tasks)',
                          '''            results = await asyncio.gather(*tasks)
            t2 = time.time()
            t3 = time.time()
            print(f"[INSTRUMENT] t2 & t3: Engine & Judge calls complete - {(t2-t1):.2f}s (Total: {(t2-t0):.2f}s)")
            
            # Print provider stats
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
            ''')

# Add t4 at end of DB writes
content = content.replace('            return [types.TextContent(type="text", text=markdown_output.strip())]',
                          '''            t4 = time.time()
            print(f"[INSTRUMENT] t4: DB writes complete - {(t4-t3):.2f}s (Total: {(t4-t0):.2f}s)")
            return [types.TextContent(type="text", text=markdown_output.strip())]''')

with open("app/mcp_server.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Instrumented app/mcp_server.py")
