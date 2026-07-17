import asyncio
from app.database import get_supabase

async def main():
    db = get_supabase()
    
    brands = db.table("brands").select("*").execute().data
    print("ALL BRANDS WITH ALIASES:")
    for b in brands:
        if len(b.get("aliases", [])) > 0:
            print(f"  {b['canonical_name']} -> {b['aliases']}")

    mentions = db.table("aeo_mentions").select("id, brand_name, run_id, workspace_id").in_("brand_name", [
        "Maui Real Estate", 
        "Salesforce Einstein", 
        "Salesforce Einstein GPT",
        "Osmo - Genius Starter Kit",
        "Google Nest (Google Assistant)",
        "Google Nest Hub (Google Assistant)"
    ]).execute().data
    
    print(f"\nMentions for these brands: {len(mentions)}")
    
    run_ids = list(set([m["run_id"] for m in mentions]))
    runs = db.table("aeo_runs").select("id, parsed_response").in_("id", run_ids).execute().data
    
    parsed_count = sum(1 for r in runs if r.get("parsed_response"))
    print(f"Runs with parsed_response: {parsed_count} / {len(runs)}")

if __name__ == "__main__":
    asyncio.run(main())
