import asyncio, json, traceback
from app.database import get_supabase

async def main():
    db = get_supabase()
    print("=== STEP 4: get_rival_analysis FULL TRACEBACK ===")
    
    # Get most recent workspace
    ws_res = db.table('aeo_runs').select('workspace_id').order('created_at', desc=True).limit(1).execute()
    if not ws_res.data:
        print("No runs found.")
        return
    
    workspace_id = ws_res.data[0]['workspace_id']
    ws_data = db.table('workspaces').select('id, brand_name, domain').eq('id', workspace_id).execute()
    workspace_data = ws_data.data[0]
    print(f"Using workspace: {workspace_data['brand_name']} / {workspace_data['domain']}")
    print()
    
    try:
        runs = db.table("aeo_runs").select(
            "id, prompt_id, engine, created_at, scan_group_id, status"
        ).eq("workspace_id", workspace_id).order("created_at", desc=True).execute().data
        
        from datetime import datetime
        latest_time_str = runs[0]["created_at"].replace('Z', '+00:00')
        latest_time = datetime.fromisoformat(latest_time_str)
        active_run_ids = set()
        for r in runs:
            r_time_str = r["created_at"].replace('Z', '+00:00')
            r_time = datetime.fromisoformat(r_time_str)
            if (latest_time - r_time).total_seconds() < 300:
                active_run_ids.add(r["id"])
        
        print(f"Active run IDs in last 5-min window: {len(active_run_ids)}")
        
        runs_filtered = [r for r in runs if r["id"] in active_run_ids]
        run_ids = [r["id"] for r in runs_filtered]
        
        mentions = db.table("aeo_mentions").select(
            "run_id, brand_name, is_target_brand"
        ).in_("run_id", run_ids).execute().data
        print(f"Mentions fetched: {len(mentions)}")
        
        from collections import defaultdict
        comp_to_mentions = defaultdict(set)
        for m in mentions:
            if not m.get("is_target_brand"):
                c_name = m.get("brand_name", "Unknown")
                comp_to_mentions[c_name].add(m["run_id"])
        
        print(f"Unique competitors: {len(comp_to_mentions)}")
        
        from app.services.consensus import compute_group_metrics, group_runs_by_scan_group, get_group_confidence
        
        comp_sov_scores = {}
        runs_grouped = group_runs_by_scan_group(runs_filtered)
        print(f"Scan groups: {len(runs_grouped)}")
        
        for comp, c_run_ids in comp_to_mentions.items():
            rate, groups, _ = compute_group_metrics(runs_filtered, c_run_ids)
            if groups > 0:
                conf_sum = sum(get_group_confidence(g, c_run_ids) for g in runs_grouped.values())
                avg_conf = int(round(conf_sum / groups)) if groups else 100
                comp_sov_scores[comp] = {
                    "share_of_voice": int(round((rate / groups) * 100)),
                    "confidence": avg_conf
                }
        
        sorted_comps = sorted(comp_sov_scores.items(), key=lambda x: x[1]["share_of_voice"], reverse=True)
        payload = {
            "summary": "Competitor AEO Landscape (Overview)",
            "rows": [
                {"name": comp, "share_of_voice": data["share_of_voice"], "confidence": data["confidence"]}
                for comp, data in sorted_comps[:10]
            ]
        }
        print("\nSUCCESS - Competitor analysis output:")
        print(json.dumps(payload, indent=2))
        
    except Exception:
        print("\nFULL TRACEBACK:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
