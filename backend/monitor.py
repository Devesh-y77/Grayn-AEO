import asyncio
from app.config import get_settings
from app.database import get_supabase

async def main():
    db = get_supabase()
    runs = db.table('aeo_runs').select('id, engine, status, created_at, error_message, pass_number').order('created_at', desc=True).limit(25).execute()
    if not runs.data:
        print("No recent runs found.")
        return
        
    print("Recent runs:")
    for r in runs.data:
        print(f"[{r['created_at']}] Engine: {r['engine']:<10} | Status: {r['status']:<15} | Pass: {r['pass_number']}")

if __name__ == "__main__":
    asyncio.run(main())
