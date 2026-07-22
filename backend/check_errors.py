import asyncio
from app.database import get_supabase

async def main():
    db = get_supabase()
    runs = db.table('aeo_runs').select('id, engine, status, raw_response, error_message').eq('status', 'error').order('created_at', desc=True).limit(2).execute()
    for r in runs.data:
        print(f"[{r['engine']}] ERROR: {r.get('error_message') or r.get('raw_response')}")

if __name__ == "__main__":
    asyncio.run(main())
