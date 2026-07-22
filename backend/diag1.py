import asyncio
from app.database import get_supabase

async def main():
    db = get_supabase()
    
    # 1. Exact query from user
    print("=== STEP 1: DEAD ENGINE ERRORS ===")
    runs = db.table('aeo_runs').select('engine, error_message, created_at').in_(
        'status', ['error', 'judge_failed']
    ).order('created_at', desc=True).limit(10).execute()
    
    for r in runs.data:
        print(f"[{r['created_at'][:19]}] {r['engine']:<12} | {r['error_message']}")

    print()
    
    # 2. What env vars each provider reads
    print("=== STEP 2: ENV VAR STATUS ===")
    from app.config import get_settings
    s = get_settings()
    checks = [
        ("OPENAI_API_KEY",      bool(s.OPENAI_API_KEY),      "openai"),
        ("ANTHROPIC_API_KEY",   bool(s.ANTHROPIC_API_KEY),   "claude"),
        ("GEMINI_API_KEY",      bool(s.GEMINI_API_KEY),      "gemini"),
        ("GROQ_API_KEY",        bool(s.GROQ_API_KEY),        "groq"),
        ("DEEPSEEK_API_KEY",    bool(s.DEEPSEEK_API_KEY),    "deepseek"),
        ("GROK_API_KEY",        bool(s.GROK_API_KEY),        "grok"),
        ("PERPLEXITY_API_KEY",  bool(s.PERPLEXITY_API_KEY),  "perplexity"),
    ]
    for var, present, engine in checks:
        status = "SET" if present else "MISSING"
        print(f"  {var:<25} -> [{status:<7}]  (engine: {engine})")
    
    print()
    
    # 3. Show stale landscape prompts
    print("=== STEP 3: STALE PROMPTS IN DB ===")
    ws_res = db.table('workspaces').select('id, brand_name, domain').execute()
    for ws in ws_res.data:
        prompts = db.table('aeo_prompts').select('id, prompt_text').eq('workspace_id', ws['id']).eq('intent', 'live_scan').execute()
        if prompts.data:
            print(f"\nWorkspace: {ws['brand_name']} / {ws['domain']} (id={ws['id']})")
            for p in prompts.data:
                print(f"  [{p['id']}] {p['prompt_text']}")

if __name__ == "__main__":
    asyncio.run(main())
