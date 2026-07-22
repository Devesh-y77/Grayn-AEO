import asyncio
from app.database import get_supabase

NETFLIX_WS_ID = "b8c66bfc-5231-49c9-a730-82ce8cee6b3c"

LANDSCAPE_IDS = [
    "e50b0725-b59b-416a-8722-f2bb682b7dde",  # Augmented reality landscape design tools
    "19f1a8f1-1d62-47e7-a118-52d37632577b",  # Best landscape design apps
    "b07ecf54-dd78-4956-b17a-6f0d45583b55",  # How to visualize landscaping ideas
    "d5a32e71-262c-429d-88e7-92012a820c4a",  # Landscape design software for professionals
    "ba06b2e8-f8cf-401d-9cb8-4aec9d22b8cc",  # Top apps for garden planning
]

async def main():
    db = get_supabase()
    
    print("=== DELETING STALE LANDSCAPE PROMPTS FROM NETFLIX WORKSPACE ===")
    for pid in LANDSCAPE_IDS:
        prompt = db.table("aeo_prompts").select("prompt_text").eq("id", pid).execute()
        text = prompt.data[0]["prompt_text"] if prompt.data else "NOT FOUND"
        db.table("aeo_prompts").delete().eq("id", pid).execute()
        print(f"  DELETED: [{pid}] {text}")
    
    print()
    print("=== REMAINING PROMPTS FOR NETFLIX WORKSPACE ===")
    remaining = db.table("aeo_prompts").select("prompt_text").eq("workspace_id", NETFLIX_WS_ID).eq("intent", "live_scan").execute()
    for p in remaining.data:
        print(f"  KEPT: {p['prompt_text']}")
    
    print()
    print("Done. Next scan will use only the above prompts (or run fresh discovery).")

if __name__ == "__main__":
    asyncio.run(main())
