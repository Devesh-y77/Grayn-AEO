import asyncio
from app.database import get_supabase
from collections import defaultdict

async def main():
    db = get_supabase()
    
    # Get last 200 runs with error info
    runs = db.table('aeo_runs').select(
        'engine, status, error_message, created_at'
    ).order('created_at', desc=True).limit(200).execute()

    if not runs.data:
        print("No runs found.")
        return

    engine_stats = defaultdict(lambda: {'ok': 0, 'error': 0, 'errors': []})

    for r in runs.data:
        eng = r['engine']
        if r['status'] == 'complete':
            engine_stats[eng]['ok'] += 1
        else:
            engine_stats[eng]['error'] += 1
            msg = r.get('error_message') or ''
            if msg and msg not in engine_stats[eng]['errors']:
                engine_stats[eng]['errors'].append(msg[:150])

    print("=" * 70)
    print(f"{'ENGINE':<14} {'OK':>5} {'FAIL':>5}  LAST ERROR")
    print("=" * 70)
    for eng in sorted(engine_stats):
        s = engine_stats[eng]
        total = s['ok'] + s['error']
        last_err = s['errors'][-1] if s['errors'] else "-"
        status = "WORKING" if s['ok'] > 0 and s['error'] == 0 else (
            "PARTIAL" if s['ok'] > 0 and s['error'] > 0 else "FAILING"
        )
        print(f"{eng:<14} {s['ok']:>5} {s['error']:>5}  [{status}]")
        if last_err and last_err != "—":
            print(f"               -> {last_err}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
