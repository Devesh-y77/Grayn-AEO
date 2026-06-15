import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env')
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SERVICE_KEY'))

ws = supabase.table('workspaces').select('id').limit(1).execute().data[0]
ws_id = ws['id']

from app.services.scoring import build_full_report
try:
    report = build_full_report(supabase, ws_id)
    print("REPORT COMPUTED SUCCESSFULLY")
    print(report.model_dump_json(indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
