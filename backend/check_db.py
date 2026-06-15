import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env')
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SERVICE_KEY'))

# Get the last 15 runs
runs = supabase.table('aeo_runs').select('*').order('created_at', desc=True).limit(15).execute()

for r in runs.data:
    print(f"ID: {r.get('id')} | Engine: {r.get('engine')} | Status: {r.get('status')} | Week: {r.get('iso_week')}")
