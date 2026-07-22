import psycopg2
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE aeo_prompts ADD CONSTRAINT aeo_prompts_workspace_id_prompt_text_key UNIQUE (workspace_id, prompt_text);")
    print("Added unique constraint.")
except Exception as e:
    print("Error:", e)
