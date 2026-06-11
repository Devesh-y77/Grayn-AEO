import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True
cur = conn.cursor()
cur.execute("ALTER TABLE aeo_mentions ADD COLUMN IF NOT EXISTS attributes JSONB DEFAULT '[]'::jsonb;")
print('done')
