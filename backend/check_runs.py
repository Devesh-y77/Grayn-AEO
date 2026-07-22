import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env')
db_url = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("SELECT id FROM aeo_workspaces WHERE client_name ILIKE '%netflix%';")
rows = cur.fetchall()
if rows:
    wid = rows[0][0]
    print(f'Netflix workspace ID: {wid}')
    cur.execute(f"SELECT count(*), status FROM aeo_runs WHERE workspace_id = '{wid}' AND created_at > '2026-07-22T14:30:00Z' GROUP BY status;")
    res = cur.fetchall()
    print('Runs:', res)
else:
    print('Netflix workspace not found.')
