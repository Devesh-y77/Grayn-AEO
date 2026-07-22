import re

with open('backend/app/services/scoring.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import if missing
if 'from app.services.db_helpers import chunked_in_fetch' not in content:
    content = content.replace('from collections import defaultdict', 'from collections import defaultdict\nfrom app.services.db_helpers import chunked_in_fetch')

# Mentions in compute_visibility
content = re.sub(
    r'mentions = \(\s*db\.table\("aeo_mentions"\)\s*\.select\("run_id, is_target_brand"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", run_ids\)\s*\.eq\("is_target_brand", True\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, is_target_brand", workspace_id, "run_id", run_ids, extra_filters={"is_target_brand": True})',
    content
)

content = re.sub(
    r'prev_mentions = \(\s*db\.table\("aeo_mentions"\)\s*\.select\("run_id"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", prev_run_ids\)\s*\.eq\("is_target_brand", True\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'prev_mentions = chunked_in_fetch(db, "aeo_mentions", "run_id", workspace_id, "run_id", prev_run_ids, extra_filters={"is_target_brand": True})',
    content
)

# Mentions in compute_share_of_voice
content = re.sub(
    r'all_mentions = \(\s*db\.table\("aeo_mentions"\)\s*\.select\("brand_name, position, run_id, sentiment"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", run_ids\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'all_mentions = chunked_in_fetch(db, "aeo_mentions", "brand_name, position, run_id, sentiment", workspace_id, "run_id", run_ids)',
    content
)

# Citations in compute_citations
content = re.sub(
    r'citations = \(\s*db\.table\("aeo_citations"\)\s*\.select\("url, domain"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", run_ids\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'citations = chunked_in_fetch(db, "aeo_citations", "url, domain", workspace_id, "run_id", run_ids)',
    content
)

# Citations in compute_competitor_sources
content = re.sub(
    r'citations = \(\s*db\.table\("aeo_citations"\)\s*\.select\("url, domain"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", run_ids\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'citations = chunked_in_fetch(db, "aeo_citations", "url, domain", workspace_id, "run_id", run_ids)',
    content
)

# Mentions in compute_competitor_sources
content = re.sub(
    r'c_mentions = \(\s*db\.table\("aeo_mentions"\)\s*\.select\("run_id"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", list\(c_run_ids\)\)\s*\.eq\("brand_name", comp_name\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'c_mentions = chunked_in_fetch(db, "aeo_mentions", "run_id", workspace_id, "run_id", list(c_run_ids), extra_filters={"brand_name": comp_name})',
    content
)

# Mentions in compute_attribute_breakdown
content = re.sub(
    r'all_mentions = \(\s*db\.table\("aeo_mentions"\)\s*\.select\("run_id, brand_name, is_target_brand"\)\s*\.eq\("workspace_id", workspace_id\)\s*\.in_\("run_id", run_ids\)\s*\.execute\(\)\s*\.data\s*or \[\]\s*\)',
    r'all_mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", run_ids)',
    content
)

# Mentions in compute_platform_scorecard
content = re.sub(
    r'mentions = db\.table\("aeo_mentions"\)\.select\("run_id, brand_name, is_target_brand"\)\.eq\("workspace_id", workspace_id\)\.in_\("run_id", \[r\["id"\] for r in runs\]\)\.execute\(\)\.data or \[\]',
    r'mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", [r["id"] for r in runs])',
    content
)

# Prompts in compute_topic_performance
content = re.sub(
    r'prompts = db\.table\("aeo_prompts"\)\.select\("id, prompt_text"\)\.eq\("workspace_id", workspace_id\)\.in_\("id", \[r\["prompt_id"\] for r in runs if r\.get\("prompt_id"\)\]\)\.execute\(\)\.data or \[\]',
    r'prompts = chunked_in_fetch(db, "aeo_prompts", "id, prompt_text", workspace_id, "id", [r["prompt_id"] for r in runs if r.get("prompt_id")])',
    content
)

# Mentions in compute_topic_performance
content = re.sub(
    r'mentions = db\.table\("aeo_mentions"\)\.select\("run_id, brand_name, is_target_brand"\)\.eq\("workspace_id", workspace_id\)\.in_\("run_id", \[r\["id"\] for r in runs\]\)\.execute\(\)\.data or \[\]',
    r'mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", [r["id"] for r in runs])',
    content
)

# Mentions in compute_historical_trend
content = re.sub(
    r'mentions = db\.table\("aeo_mentions"\)\.select\("run_id, brand_name, is_target_brand"\)\.eq\("workspace_id", workspace_id\)\.in_\("run_id", run_ids\)\.execute\(\)\.data or \[\]',
    r'mentions = chunked_in_fetch(db, "aeo_mentions", "run_id, brand_name, is_target_brand", workspace_id, "run_id", run_ids)',
    content
)

with open('backend/app/services/scoring.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched scoring.py!")
