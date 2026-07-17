import asyncio
from app.database import get_supabase
db = get_supabase()

def print_cluster(prefixes):
    for p in prefixes:
        brands = db.table('brands').select('*').ilike('canonical_name', f'{p}%').execute().data
        for b in brands:
            count = db.table('aeo_mentions').select('id', count='exact').eq('brand_id', b['id']).execute().count
            print(f"- Brand '{b['canonical_name']}' (aliases: {b['aliases']}): {count} mentions")

print_cluster(['Salesforce Einstein', 'Osmo', 'Google Nest', 'Maui', 'Kauai', 'Hawaii'])
