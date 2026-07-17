from app.database import get_supabase

db = get_supabase()
res = db.table('aeo_runs').select('id, engine, created_at, workspaces(brand_name, domain), aeo_prompts(prompt_text)').order('created_at', desc=True).limit(5).execute()

for i, r in enumerate(res.data):
    ws = r.get('workspaces') or {}
    pmpt = r.get('aeo_prompts') or {}
    print(f"{i+1}. Brand: {ws.get('brand_name')} ({ws.get('domain')}) - Engine: {r['engine']} - Query: {pmpt.get('prompt_text')} - Time: {r['created_at']}")
