import psycopg2
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
cur = conn.cursor()

cur.execute("""
SELECT conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'aeo_prompts';
""")
print(cur.fetchall())
