import re
import asyncio
from rapidfuzz import fuzz
from typing import Tuple, Dict, Any, List, Optional

_workspace_locks: Dict[str, asyncio.Lock] = {}

# How long to wait for the per-workspace write lock before giving up on
# persisting a new brand/alias for this one mention. A stuck lock must
# never hang the whole scan (see the brand_normalizer performance fix —
# this, combined with unbatched per-mention DB reads, caused an 8-minute
# production hang).
LOCK_TIMEOUT_SECONDS = 5.0

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

async def load_brand_cache(workspace_id: str, db) -> List[Dict[str, Any]]:
    """
    Fetch all known brands for a workspace ONCE, up front.

    Callers processing many mentions in a single scan (e.g. mcp_server.py's
    run_single, across every query x engine x pass) MUST call this once
    before dispatching their tasks and pass the result into every
    normalize() call as brand_cache — otherwise each mention re-fetches the
    entire brands table from scratch. That N+1 pattern, serialized through
    the per-workspace lock below, is what caused an 8-minute production
    scan hang: hundreds of redundant blocking reads queued one at a time.
    """
    res = await asyncio.to_thread(
        lambda: db.table("brands").select("*").eq("workspace_id", workspace_id).execute()
    )
    return res.data or []


def _find_best_match(raw: str, cleaned: str, existing: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
    return best_match


async def normalize(
    raw: str, workspace_id: str, db, brand_cache: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, str]:
    """
    Normalizes a raw brand mention. Returns (canonical_name, brand_id).

    brand_cache should be the list returned by load_brand_cache(), fetched
    ONCE per scan and reused across every mention — see that function's
    docstring for why. When brand_cache is None, this falls back to a
    fresh single fetch (fine for low-volume/one-off callers, not for a
    scan processing many mentions).

    Writes (new alias, new brand) are still serialized through a
    per-workspace lock for correctness, but the lock now has a timeout —
    a stuck write can no longer hang the entire scan; it just skips
    persisting that one update and returns the match found so far.
    """
    cleaned = clean_brand_name(raw)
    if not cleaned:
        return raw, None

    if brand_cache is not None:
        existing = brand_cache
    else:
        existing = await asyncio.to_thread(
            lambda: db.table("brands").select("*").eq("workspace_id", workspace_id).execute()
        )
        existing = existing.data or []

    best_match = _find_best_match(raw, cleaned, existing)

    if best_match:
        brand_id = best_match["id"]
        canonical = best_match["canonical_name"]
        aliases = set(best_match.get("aliases") or [])
        aliases.add(canonical)

        if raw not in aliases:
            aliases_list = best_match.get("aliases") or []
            aliases_list.append(raw)
            lock = get_lock(workspace_id)
            try:
                await asyncio.wait_for(lock.acquire(), timeout=LOCK_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                # Couldn't get the write lock in time — return the match we
                # already found rather than block the scan on it. The new
                # alias just won't be recorded from this particular mention.
                return canonical, brand_id
            try:
                await asyncio.to_thread(
                    lambda: db.table("brands").update({"aliases": aliases_list}).eq("id", brand_id).execute()
                )
                best_match["aliases"] = aliases_list  # keep the shared cache consistent
            finally:
                lock.release()

        return canonical, brand_id

    else:
        # No match found — insert new brand (upsert on workspace_id, canonical_name)
        lock = get_lock(workspace_id)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=LOCK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            # Couldn't safely insert right now — return the raw name rather
            # than hang; a later mention for the same brand will retry.
            return raw, None
        try:
            res = await asyncio.to_thread(
                lambda: db.table("brands").upsert({
                    "workspace_id": workspace_id,
                    "canonical_name": raw,
                    "aliases": [raw]
                }, on_conflict="workspace_id,canonical_name").execute()
            )
            if res.data:
                inserted = res.data[0]
                if brand_cache is not None:
                    brand_cache.append(inserted)  # keep the shared cache consistent for later mentions
                return inserted["canonical_name"], inserted["id"]
            return raw, None
        finally:
            lock.release()
