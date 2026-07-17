import asyncio
import os
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from app.database import get_supabase
from app.services.judge import extract_mentions_and_citations
from app.services.brand_normalizer import normalize

async def main():
    db = get_supabase()
    
    print("=== PART 1: TOP-UP NORMALIZATION (brand_id IS NULL) ===")
    unnormalized = db.table("aeo_mentions").select("id, brand_name, workspace_id").is_("brand_id", "null").execute().data
    print(f"Found {len(unnormalized)} un-normalized mentions from recent tracking.py runs.")
    
    for m in unnormalized:
        raw = m["brand_name"]
        workspace_id = m["workspace_id"]
        canonical_m, brand_id = await normalize(raw, workspace_id, db)
        print(f"  Top-up: {raw} -> {canonical_m} (ID: {brand_id})")
        
        # Don't execute updates in dry-run, we just print them.
        # db.table("aeo_mentions").update({
        #    "brand_name": canonical_m,
        #    "raw_name": raw,
        #    "brand_id": brand_id
        # }).eq("id", m["id"]).execute()

    print("\n=== PART 2: BAD MERGE REPAIR (Re-running Judge) ===")
    
    bad_merges = [
        "Maui Real Estate",
        "Salesforce Einstein GPT",
        "Salesforce Einstein",
        "Osmo - Genius Starter Kit",
        "Google Nest (Google Assistant)",
        "Google Nest Hub (Google Assistant)"
    ]
    
    # 1. Fetch mention rows for these
    mentions = db.table("aeo_mentions").select("id, brand_name, run_id, workspace_id, position, sentiment").in_("brand_name", bad_merges).execute().data
    print(f"Found {len(mentions)} corrupted mention rows.")
    
    # 2. Fetch the runs
    run_ids = list(set([m["run_id"] for m in mentions]))
    runs = db.table("aeo_runs").select("id, raw_response, workspace_id").in_("id", run_ids).execute().data
    print(f"Need to re-process {len(runs)} runs.")
    
    for r in runs:
        ws = db.table("workspaces").select("brand_name, aliases").eq("id", r["workspace_id"]).single().execute().data
        target_brand = ws.get("brand_name", "")
        aliases = ws.get("aliases") or []
        
        print(f"\nRe-running Judge for run {r['id']} (Workspace target: {target_brand})...")
        
        old_mentions_for_run = [m for m in mentions if m["run_id"] == r["id"]]
        
        if not r.get("raw_response"):
            print("  [!] WARNING: raw_response is NULL for this run! Cannot run Judge.")
            for old_m in old_mentions_for_run:
                print(f"  -> Dry Run Fix (AMBIGUOUS): DELETE FROM aeo_mentions WHERE id='{old_m['id']}' (Original string lost; defaulting to deletion rather than guessing between '{old_m['brand_name']}' variations)")
                if "--commit" in sys.argv:
                    db.table("aeo_mentions").delete().eq("id", old_m["id"]).execute()
            continue
            
        ext = await extract_mentions_and_citations(r["raw_response"], target_brand, aliases, skip_citations=True)
        print(f"  New extraction returned: {[e.brand_name for e in ext.mentions]}")
        for old_m in old_mentions_for_run:
            # Match by finding the extraction that is most similar to the old corrupted brand_name
            # Or specifically look for the known true brand names in the new extraction
            expected_fragments = ["Kauai", "Maui", "Salesforce", "Einstein", "Osmo", "Nest", "Google"]
            
            best_match = None
            best_score = 0
            for e in ext.mentions:
                # If they share significant words, it's the same brand mention
                w1 = set(old_m["brand_name"].lower().split())
                w2 = set(e.brand_name.lower().split())
                score = len(w1.intersection(w2))
                if score > best_score:
                    best_score = score
                    best_match = e
            
            if best_match:
                raw_extracted = best_match.brand_name
                print(f"  Matched mention {old_m['id']}: Originally '{raw_extracted}' (Corrupted as '{old_m['brand_name']}')")
                
                # Normalize the newly extracted string to fix it
                canonical_m, brand_id = await normalize(raw_extracted, r["workspace_id"], db)
                print(f"  -> Dry Run Fix: UPDATE aeo_mentions SET brand_name='{canonical_m}', raw_name='{raw_extracted}', brand_id='{brand_id}' WHERE id='{old_m['id']}'")
                if "--commit" in sys.argv:
                    db.table("aeo_mentions").update({
                        "brand_name": canonical_m,
                        "raw_name": raw_extracted,
                        "brand_id": brand_id
                    }).eq("id", old_m["id"]).execute()
            else:
                print(f"  Failed to match mention {old_m['id']} (Corrupted: {old_m['brand_name']}) in new extraction.")

    print("\n=== PART 3: CLEANING CORRUPTED ALIASES ===")
    # We must remove the wrongly merged aliases from the canonical brands.
    # The normalizer upsert above won't automatically remove an alias from the wrong cluster, 
    # it just ensures the right cluster exists. So we remove them manually here.
    
    to_remove = {
        "Maui Real Estate": ["Kauai Real Estate"],
        "Salesforce Einstein GPT": ["Salesforce Einstein"],
        "Salesforce Einstein": ["Salesforce Einstein GPT"],
        "Osmo - Genius Starter Kit": ["Osmo - Little Genius Starter Kit"],
        "Google Nest (Google Assistant)": ["Google Nest Hub (Google Assistant)"],
        "Google Nest Hub (Google Assistant)": ["Google Nest (Google Assistant)"]
    }
    
    brands = db.table("brands").select("*").in_("canonical_name", list(to_remove.keys())).execute().data
    for b in brands:
        current_aliases = b.get("aliases") or []
        removals = to_remove.get(b["canonical_name"], [])
        new_aliases = [a for a in current_aliases if a not in removals]
        if len(new_aliases) != len(current_aliases):
            print(f"Dry Run Fix: UPDATE brands SET aliases={new_aliases} WHERE id='{b['id']}' (Removed {removals})")
            if "--commit" in sys.argv:
                db.table("brands").update({"aliases": new_aliases}).eq("id", b["id"]).execute()

if __name__ == "__main__":
    asyncio.run(main())
