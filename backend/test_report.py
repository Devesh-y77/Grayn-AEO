import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.scoring import build_full_report, compute_historical_trend

async def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    db = create_client(url, key)
    
    ws = db.table("workspaces").select("*").limit(1).execute()
    if not ws.data:
        print("No workspaces")
        return
    ws_id = ws.data[0]["id"]
    
    print("Testing historical trend...")
    trend = compute_historical_trend(db, ws_id)
    print("Trend:", trend)
    
    print("\nTesting build_full_report...")
    try:
        report = await build_full_report(db, ws_id)
        print("Report visibility:", report.visibility)
        print("Report AI Insight:", report.ai_insight)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
