import asyncio
from app.database import get_supabase
db = get_supabase()
from datetime import datetime

# Get the most recent run's created_at
recent = db.table("aeo_runs").select("created_at, workspace_id").order("created_at", desc=True).limit(1).execute()
if not recent.data:
    print("No runs found.")
    exit(0)

latest_time_str = recent.data[0]["created_at"]
workspace_id = recent.data[0]["workspace_id"]
latest_time = datetime.fromisoformat(latest_time_str.replace('Z', '+00:00'))

# Fetch all runs for this workspace that happened within 5 minutes of the latest run
runs = db.table("aeo_runs").select("id, cost_usd, created_at").eq("workspace_id", workspace_id).order("created_at", desc=True).execute()

total_usd = 0.0
runs_count = 0
for r in runs.data:
    r_time = datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))
    diff = (latest_time - r_time).total_seconds()
    if diff <= 300: # 5 minutes
        cost = r.get("cost_usd") or 0.0
        total_usd += float(cost)
        runs_count += 1

# Conversion rate assumption: 1 USD = ~83.5 INR
total_inr = total_usd * 83.5

print(f"Total Runs: {runs_count}")
print(f"Total Cost (USD): ${total_usd:.4f}")
print(f"Total Cost (INR): ₹{total_inr:.4f}")
