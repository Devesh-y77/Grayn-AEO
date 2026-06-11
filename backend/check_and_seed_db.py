"""
Check Database Schema and Seed Initial Mock Data for Grayn AEO

Connects directly via psycopg2.
If tables do not exist, runs schema.sql.
Seeds a default workspace, an active API key, tracked competitors,
topic clusters, and several weeks of historical run data.
"""

import os
import json
import hashlib
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment!")
    exit(1)

# Hashed API key setup
RAW_KEY = "gk_devprefix_devsecretkey123456789"
KEY_PREFIX = "gk_devprefix_"
KEY_HASH = hashlib.sha256(RAW_KEY.encode()).hexdigest()

print(f"Connecting to database...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
except Exception as e:
    print(f"Failed to connect to database: {e}")
    exit(1)


def tables_exist():
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'workspaces'
        );
    """
    )
    return cur.fetchone()[0]


# 1. Create Schema if needed
if not tables_exist():
    print("Tables not found. Running schema.sql...")
    try:
        with open("schema.sql", "r") as f:
            schema_sql = f.read()
        cur.execute(schema_sql)
        print("Schema created successfully.")
    except Exception as e:
        print(f"Failed to run schema.sql: {e}")
        conn.close()
        exit(1)
else:
    print("Database tables already exist.")

# 2. Seed Default Workspace
cur.execute("SELECT id FROM workspaces WHERE brand_name = 'Acme Corp' LIMIT 1;")
ws_row = cur.fetchone()
if not ws_row:
    print("Seeding default workspace 'Acme Corp'...")
    cur.execute(
        """
        INSERT INTO workspaces (brand_name, domain, aliases, brand_context)
        VALUES (
            'Acme Corp', 
            'acme.com', 
            ARRAY['Acme', 'Acme Systems', 'Acme Software'], 
            'Acme Corp is a leading cloud infrastructure provider specializing in serverless hosting and developer tools.'
        ) RETURNING id;
    """
    )
    workspace_id = cur.fetchone()[0]
else:
    workspace_id = ws_row[0]

print(f"Workspace ID: {workspace_id}")

# 3. Seed Default API Key
cur.execute("SELECT id FROM api_keys WHERE key_hash = %s LIMIT 1;", (KEY_HASH,))
key_row = cur.fetchone()
if not key_row:
    print(f"Seeding API key: {RAW_KEY}")
    cur.execute(
        """
        INSERT INTO api_keys (workspace_id, key_prefix, key_hash, revoked)
        VALUES (%s, %s, %s, false);
    """,
        (workspace_id, KEY_PREFIX, KEY_HASH),
    )
else:
    print("API Key already exists.")

# 4. Seed Tracked Competitors
cur.execute("SELECT count(*) FROM aeo_competitors WHERE workspace_id = %s;", (workspace_id,))
if cur.fetchone()[0] == 0:
    print("Seeding competitors...")
    competitors = [
        ("Vercel", "vercel.com", ["Vercel", "Next.js"]),
        ("Netlify", "netlify.com", ["Netlify"]),
        ("Heroku", "heroku.com", ["Heroku"]),
    ]
    for brand, dom, aliases in competitors:
        cur.execute(
            """
            INSERT INTO aeo_competitors (workspace_id, brand_name, domain, aliases)
            VALUES (%s, %s, %s, %s);
        """,
            (workspace_id, brand, dom, aliases),
        )

# 5. Seed Topic Clusters
cur.execute("SELECT count(*) FROM aeo_clusters WHERE workspace_id = %s;", (workspace_id,))
if cur.fetchone()[0] == 0:
    print("Seeding clusters...")
    clusters = [
        ("Serverless Hosting Comparison", 45000, 45.0, 75.0, "write-new"),
        ("Developer Tools & DX", 22000, 65.5, 34.5, "refresh"),
        ("Edge Computing Performance", 15000, 20.0, 90.0, "expand"),
        ("Cloud Infrastructure Cost", 30000, 80.0, 20.0, "refresh"),
    ]
    for name, vol, vis, opp, action in clusters:
        cur.execute(
            """
            INSERT INTO aeo_clusters (workspace_id, cluster_name, search_volume, brand_ai_visibility, opportunity_score, refill_action)
            VALUES (%s, %s, %s, %s, %s, %s);
        """,
            (workspace_id, name, vol, vis, opp, action),
        )

# 6. Seed Prompts
cur.execute("SELECT count(*) FROM aeo_prompts WHERE workspace_id = %s;", (workspace_id,))
if cur.fetchone()[0] == 0:
    print("Seeding prompts...")
    prompts = [
        ("Which serverless hosting platform is best for next.js in 2026?", "transactional", "developer", "Serverless Hosting Comparison"),
        ("How does Acme Corp compare to Vercel for hosting serverless APIs?", "commercial", "developer", "Serverless Hosting Comparison"),
        ("What are the advantages of edge computing over traditional hosting?", "informational", "architect", "Edge Computing Performance"),
        ("Which developer platforms offer the best DX?", "commercial", "developer", "Developer Tools & DX"),
        ("How can we reduce cloud infrastructure bills?", "informational", "executive", "Cloud Infrastructure Cost"),
    ]
    for text, intent, persona, cluster in prompts:
        cur.execute(
            """
            INSERT INTO aeo_prompts (workspace_id, prompt_text, intent, persona, topic_cluster)
            VALUES (%s, %s, %s, %s, %s);
        """,
            (workspace_id, text, intent, persona, cluster),
        )

# Get prompt list for run association
cur.execute("SELECT id, prompt_text FROM aeo_prompts WHERE workspace_id = %s;", (workspace_id,))
db_prompts = cur.fetchall()

# 7. Seed Runs, Mentions, and Citations for past 3 weeks
cur.execute("SELECT count(*) FROM aeo_runs WHERE workspace_id = %s;", (workspace_id,))
if cur.fetchone()[0] == 0:
    print("Seeding historical AEO runs/mentions/citations...")
    weeks = ["2026-W21", "2026-W22", "2026-W23"]
    engines = ["openai", "gemini", "google_ai", "perplexity", "grok"]
    
    # Pre-defined mock answers for mentions/citations seeding
    for week_idx, week in enumerate(weeks):
        for engine in engines:
            for prompt_id, prompt_text in db_prompts:
                # Visibility percentage climbs week over week
                # Let's mock a structured response and mentions
                is_mentioned = False
                # Acme is mentioned in:
                # Week 21: some prompts (visibility ~30%)
                # Week 22: more prompts (visibility ~45%)
                # Week 23: most prompts (visibility ~60%)
                if week == "2026-W21" and prompt_text.startswith("How does Acme"):
                    is_mentioned = True
                elif week == "2026-W22" and (prompt_text.startswith("How does Acme") or "developer platforms" in prompt_text):
                    is_mentioned = True
                elif week == "2026-W23" and not prompt_text.startswith("How can we"):
                    is_mentioned = True

                raw_resp = f"Response from {engine} in week {week} for query '{prompt_text}'."
                parsed_resp = {
                    "mentions": [
                        {
                            "brand_name": "Acme Corp", "is_target_brand": True, "sentiment": "positive", "position": 1,
                            "attributes": [{"name": "Developer Experience", "sentiment": "positive"}]
                        } if is_mentioned else {},
                        {
                            "brand_name": "Vercel", "is_target_brand": False, "sentiment": "neutral", "position": 2,
                            "attributes": [{"name": "Pricing", "sentiment": "negative"}]
                        },
                    ]
                }
                
                # Filter empty dicts
                parsed_resp["mentions"] = [m for m in parsed_resp["mentions"] if m]

                cur.execute(
                    """
                    INSERT INTO aeo_runs (workspace_id, prompt_id, engine, iso_week, raw_response, parsed_response, cost_usd, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 0.0015, 'complete') RETURNING id;
                """,
                    (workspace_id, prompt_id, engine, week, raw_resp, json.dumps(parsed_resp)),
                )
                run_id = cur.fetchone()[0]

                # Seed Mentions
                if is_mentioned:
                    cur.execute(
                        """
                        INSERT INTO aeo_mentions (workspace_id, run_id, brand_name, is_target_brand, position, sentiment, attributes)
                        VALUES (%s, %s, 'Acme Corp', true, 1, 'positive', %s);
                    """,
                        (workspace_id, run_id, json.dumps([{"name": "Developer Experience", "sentiment": "positive"}])),
                    )
                
                cur.execute(
                    """
                    INSERT INTO aeo_mentions (workspace_id, run_id, brand_name, is_target_brand, position, sentiment, attributes)
                    VALUES (%s, %s, 'Vercel', false, 2, 'neutral', %s);
                """,
                    (workspace_id, run_id, json.dumps([{"name": "Pricing", "sentiment": "negative"}])),
                )

                # Seed Citations
                cur.execute(
                    """
                    INSERT INTO aeo_citations (workspace_id, run_id, url, domain, source_type)
                    VALUES (%s, %s, 'https://vercel.com/docs/concepts', 'vercel.com', 'documentation');
                """,
                    (workspace_id, run_id),
                )
                if is_mentioned:
                    cur.execute(
                        """
                        INSERT INTO aeo_citations (workspace_id, run_id, url, domain, source_type)
                        VALUES (%s, %s, 'https://acme.com/blog/serverless-hosting', 'acme.com', 'blog');
                    """,
                        (workspace_id, run_id),
                    )

print("Database checking and seeding completed successfully!")
conn.close()
