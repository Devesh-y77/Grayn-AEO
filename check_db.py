import psycopg2
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='aeo_prompts' AND column_name='intent';")
rows = cur.fetchall()
print("Intent column exists:", bool(rows))

if rows:
    cur.execute("SELECT COUNT(*) FROM aeo_prompts WHERE intent='live_scan';")
    count = cur.fetchone()[0]
    print(f"live_scan count: {count}")
else:
    cur.execute("SELECT COUNT(*) FROM aeo_prompts;")
    count = cur.fetchone()[0]
    print(f"total aeo_prompts count: {count}")
