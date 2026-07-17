import os
import sys
import asyncio
from app.database import get_supabase
from app.services import tracking
import uuid

async def run_migration():
    db = get_supabase()
    
    workspace_id = str(uuid.uuid4())
    print(f"Creating workspace gomoterra.com with ID: {workspace_id}")
    
    # 1. Create Workspace
    ws_data = {
        "id": workspace_id,
        "brand_name": "Gomoterra",
        "domain": "gomoterra.com",
        "aliases": ["Gomoterra"],
        "brand_context": "A peer-to-peer campervan rental marketplace connecting owners with travelers.",
        "target_location": "United States",
    }
    db.table("workspaces").insert(ws_data).execute()
    
    # 2. Create Topic Cluster
    cluster_name = "Campervan Rentals & Alternatives"
    cluster_data = {
        "workspace_id": workspace_id,
        "cluster_name": cluster_name,
        "search_volume": 12500,
        "brand_ai_visibility": 0,
        "opportunity_score": 95,
        "refill_action": "write-new",
    }
    db.table("aeo_clusters").insert(cluster_data).execute()
    
    # 3. Create Prompts
    prompts = [
        "Best alternatives to gomoterra.com",
        "Top services like gomoterra.com",
        "gomoterra.com reviews",
    ]
    for prompt_text in prompts:
        prompt_data = {
            "workspace_id": workspace_id,
            "prompt_text": prompt_text,
            "topic_cluster": cluster_name,
            "intent": "comparison",
            "is_active": True,
        }
        db.table("aeo_prompts").insert(prompt_data).execute()
        
    print("Prompts inserted. Triggering batch run...")
    
    # 4. Trigger tracking batch run
    workspace = db.table("workspaces").select("*").eq("id", workspace_id).single().execute().data
    
    try:
        result = await tracking.trigger_batch_run(db, workspace)
        print("Batch run complete:", result)
    except Exception as e:
        print("Error during batch run:", e)
        
if __name__ == "__main__":
    asyncio.run(run_migration())
