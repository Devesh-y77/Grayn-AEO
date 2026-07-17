import os
import psycopg2
import psycopg2.extras
from rapidfuzz import fuzz
from collections import defaultdict
import re
import sys

def clean_brand_name(raw: str) -> str:
    cleaned = raw.lower().strip()
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    for suffix in [".com", ".ai", ".io", ".co", ".app", ".org", ".net", ".inc", ".ltd"]:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def extract_digits(s: str) -> list[str]:
    return re.findall(r'\d+', s)

def extract_trailing_symbols(s: str) -> str:
    match = re.search(r'[^a-zA-Z0-9]+$', s)
    return match.group(0) if match else ""

def is_valid_merge(raw1: str, raw2: str, clean1: str, clean2: str) -> bool:
    if extract_digits(clean1) != extract_digits(clean2):
        return False
    if extract_trailing_symbols(clean1) != extract_trailing_symbols(clean2):
        return False
    return True

def has_domain_suffix(raw: str) -> bool:
    lower_raw = raw.lower()
    for suffix in [".com", ".ai", ".io", ".co", ".app", ".org", ".net", ".inc", ".ltd"]:
        if lower_raw.endswith(suffix):
            return True
    return False

def run_backfill(commit: bool = False):
    db_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        print("Fetching mentions...")
        cur.execute("SELECT id, workspace_id, brand_name FROM aeo_mentions")
        mentions = cur.fetchall()
        
        simulated_brands = defaultdict(list)
        
        print(f"Processing {len(mentions)} mentions...")
        for m in mentions:
            raw = m["brand_name"]
            if not raw:
                continue
            wid = m["workspace_id"]
            
            cleaned = clean_brand_name(raw)
            if not cleaned:
                continue
                
            brands_for_ws = simulated_brands[wid]
            best_match = None
            best_score = 0
            
            for b in brands_for_ws:
                for alias in b["aliases"]:
                    alias_clean = clean_brand_name(alias)
                    score = fuzz.ratio(cleaned, alias_clean)
                    
                    if score >= 90:
                        if is_valid_merge(raw, alias, cleaned, alias_clean):
                            if score > best_score:
                                best_score = score
                                best_match = b
                                
            if best_match:
                best_match["aliases"].add(raw)
                best_match["raw_counts"][raw] = best_match["raw_counts"].get(raw, 0) + 1
                best_match["mentions"] += 1
                best_match["mention_ids"].append(m["id"])
            else:
                brands_for_ws.append({
                    "raw_counts": {raw: 1},
                    "aliases": {raw},
                    "mentions": 1,
                    "mention_ids": [m["id"]]
                })
                
        if not commit:
            print("Dry run complete. Use --commit to apply to database.")
            return
            
        print("Committing to database...")
        for wid, brands in simulated_brands.items():
            for b in brands:
                canonical = sorted(
                    b["raw_counts"].items(), 
                    key=lambda x: (not has_domain_suffix(x[0]), x[1], len(x[0])), 
                    reverse=True
                )[0][0]
                
                aliases_list = list(b["aliases"])
                
                # Insert brand using psycopg2 upsert
                import json
                cur.execute("""
                    INSERT INTO brands (workspace_id, canonical_name, aliases)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (workspace_id, canonical_name) 
                    DO UPDATE SET aliases = EXCLUDED.aliases
                    RETURNING id
                """, (wid, canonical, json.dumps(aliases_list)))
                
                res = cur.fetchone()
                if res:
                    brand_id = res["id"]
                    
                    # Update mentions
                    for chunk in [b["mention_ids"][i:i+100] for i in range(0, len(b["mention_ids"]), 100)]:
                        cur.execute("""
                            UPDATE aeo_mentions 
                            SET brand_id = %s, brand_name = %s
                            WHERE id = ANY(%s::uuid[])
                        """, (brand_id, canonical, chunk))
                        
        print("Backfill complete.")

if __name__ == "__main__":
    commit = "--commit" in sys.argv
    run_backfill(commit=commit)
