import os, sys
from dotenv import load_dotenv
sys.path.insert(0, 'backend')
load_dotenv('backend/.env')
from app.database import get_supabase
from collections import Counter

db = get_supabase()
wid = 'b8c66bfc-5231-49c9-a730-82ce8cee6b3c'

# ── Item 4: Gemini diagnostic ──────────────────────────────
res = db.table('aeo_runs').select('engine, status, error_message').eq('workspace_id', wid).eq('engine', 'gemini').execute().data
status_count = Counter(r['status'] for r in res)
errors = list(set(r['error_message'] for r in res if r.get('error_message')))
print("=== GEMINI DIAGNOSTIC ===")
print('Status counts:', dict(status_count))
print('Error samples (first 2):')
for e in errors[:2]:
    print(' ', str(e)[:200])

# ── Item 1: Netflix India false negatives ──────────────────
print("\n=== ITEM 1: NETFLIX* IS_TARGET_BRAND=FALSE ===")
bad = db.table('aeo_mentions').select('id, brand_name, is_target_brand').eq('workspace_id', wid).eq('is_target_brand', False).ilike('brand_name', 'Netflix%').execute().data
print(f'Affected rows: {len(bad)}')
for b in bad[:10]:
    print(f'  id={b["id"]}  brand={b["brand_name"]}')

# ── Item 3: Case-sensitive duplicate prompts ───────────────
print("\n=== ITEM 3: DUPLICATE PROMPTS (CASE-INSENSITIVE) ===")
prompts = db.table('aeo_prompts').select('id, prompt_text, created_at').eq('workspace_id', wid).execute().data
seen = {}
dups = []
for p in sorted(prompts, key=lambda x: x['created_at']):
    key = p['prompt_text'].strip().lower()
    if key in seen:
        dups.append({'keep': seen[key], 'dup': p})
    else:
        seen[key] = p
print(f'Duplicate count: {len(dups)}')
for d in dups:
    keep_text = d['keep']['prompt_text']
    dup_text = d['dup']['prompt_text']
    dup_id = d['dup']['id']
    print(f'  KEEP id={d["keep"]["id"]} "{keep_text}"')
    print(f'  DROP id={dup_id}           "{dup_text}"')
    # Count runs pointing to dup
    runs = db.table('aeo_runs').select('id').eq('prompt_id', dup_id).execute().data
    print(f'  -> {len(runs)} runs reference dup prompt')
