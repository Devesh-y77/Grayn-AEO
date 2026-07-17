import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()

from app.database import get_supabase
from app.services.brand_normalizer import get_word_multiset, clean_brand_name

async def main():
    db = get_supabase()
    
    print("=== RETROACTIVE TOKEN MULTISET AUDIT ===")
    brands = db.table("brands").select("*").execute().data
    
    flagged = 0
    checked = 0
    
    for b in brands:
        canonical_raw = b["canonical_name"]
        canonical_clean = clean_brand_name(canonical_raw)
        canonical_multiset = get_word_multiset(canonical_clean)
        
        aliases = b.get("aliases") or []
        for alias in aliases:
            if alias == canonical_raw:
                continue
            
            checked += 1
            alias_clean = clean_brand_name(alias)
            alias_multiset = get_word_multiset(alias_clean)
            
            diff = canonical_multiset.symmetric_difference(alias_multiset)
            if len(diff) > 0:
                print(f"FLAGGED BAD MERGE:")
                print(f"  Canonical: '{canonical_raw}' -> {canonical_multiset}")
                print(f"  Alias:     '{alias}' -> {alias_multiset}")
                print(f"  Diff:      {diff}\n")
                flagged += 1

    print(f"Audit Complete. Checked {checked} aliases.")
    print(f"Flagged {flagged} bad merges.")

if __name__ == "__main__":
    asyncio.run(main())
