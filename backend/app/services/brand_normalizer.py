import re
import asyncio
from rapidfuzz import fuzz
from typing import Tuple, Dict, Any

_workspace_locks: Dict[str, asyncio.Lock] = {}

def get_lock(workspace_id: str) -> asyncio.Lock:
    if workspace_id not in _workspace_locks:
        _workspace_locks[workspace_id] = asyncio.Lock()
    return _workspace_locks[workspace_id]

def clean_brand_name(raw: str) -> str:
    # Split camelCase before lowercasing (e.g. HawaiiLife -> Hawaii Life)
    raw = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw)
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

def get_word_multiset(s: str) -> set:
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'(?<=[a-zA-Z])(?=\d)', ' ', s)
    s = re.sub(r'(?<=\d)(?=[a-zA-Z])', ' ', s)
    return set(s.split())

def is_valid_merge(raw1: str, raw2: str, clean1: str, clean2: str) -> bool:
    if extract_digits(clean1) != extract_digits(clean2):
        return False
    if extract_trailing_symbols(clean1) != extract_trailing_symbols(clean2):
        return False
        
    ta = get_word_multiset(clean1)
    tb = get_word_multiset(clean2)
    if len(ta.symmetric_difference(tb)) > 0:
        return False
            
    return True

def has_domain_suffix(raw: str) -> bool:
    lower_raw = raw.lower()
    for suffix in [".com", ".ai", ".io", ".co", ".app", ".org", ".net", ".inc", ".ltd"]:
        if lower_raw.endswith(suffix):
            return True
    return False

async def normalize(raw: str, workspace_id: str, db) -> Tuple[str, str]:
    """
    Normalizes a raw brand mention.
    Returns (canonical_name, brand_id).
    """
    cleaned = clean_brand_name(raw)
    if not cleaned:
        return raw, None
        
    async with get_lock(workspace_id):
        # Fetch existing brands for this workspace
        existing = db.table("brands").select("*").eq("workspace_id", workspace_id).execute().data or []
        
        best_match = None
        best_score = 0
        
        for brand in existing:
            # We match against canonical_name and all aliases
            variants_to_check = [brand["canonical_name"]] + (brand.get("aliases") or [])
            
            for alias in variants_to_check:
                alias_clean = clean_brand_name(alias)
                score = fuzz.ratio(cleaned, alias_clean)
                
                if score >= 90:
                    if is_valid_merge(raw, alias, cleaned, alias_clean):
                        if score > best_score:
                            best_score = score
                            best_match = brand
                            
        if best_match:
            brand_id = best_match["id"]
            canonical = best_match["canonical_name"]
            aliases = set(best_match.get("aliases") or [])
            aliases.add(canonical)
            
            if raw not in aliases:
                aliases_list = best_match.get("aliases") or []
                aliases_list.append(raw)
                # Update aliases in DB
                db.table("brands").update({"aliases": aliases_list}).eq("id", brand_id).execute()
                
            return canonical, brand_id
            
        else:
            # No match found, insert new brand
            # Upsert using unique constraint (workspace_id, canonical_name)
            res = db.table("brands").upsert({
                "workspace_id": workspace_id,
                "canonical_name": raw,
                "aliases": [raw]
            }, on_conflict="workspace_id,canonical_name").execute()
            
            if res.data:
                inserted = res.data[0]
                return inserted["canonical_name"], inserted["id"]
            return raw, None
