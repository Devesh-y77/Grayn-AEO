import asyncio
import time
from app.mcp_server import server
import os
from dotenv import load_dotenv

async def run_local():
    load_dotenv("backend/.env")
    
    class MockContext:
        @property
        def session_id(self):
            return "test-session"
    
    from app.database import get_supabase
    db = get_supabase()
    ws_res = db.table("workspaces").select("id").limit(1).execute()
    workspace_id = ws_res.data[0]["id"]
    
    print("Running trigger_aeo_analysis directly...")
    t0 = time.time()
    from app.mcp_server import handle_call_tool
    try:
        result = await handle_call_tool(
            "trigger_aeo_analysis",
            arguments={
                "url": "netflix.com",
                "location": "India",
                "queries": 10,
                "models": ["openai", "claude", "gemini", "perplexity", "deepseek", "groq"],
                "passes": 3,
                "workspace_ref": workspace_id,
                "force_rediscovery": False
            }
        )
        t1 = time.time()
        print(f"Finished in {t1 - t0:.2f}s")
        print(result[0].text if result else "No output")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_local())
