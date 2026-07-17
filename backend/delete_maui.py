import asyncio
from app.database import get_supabase
db = get_supabase()
# Find brand
brand = db.table('brands').select('id').eq('canonical_name', 'Maui Real Estate').execute().data
if brand:
    brand_id = brand[0]['id']
    print(f"Dry Run: DELETE FROM aeo_mentions WHERE brand_id = '{brand_id}'")
    print(f"Dry Run: DELETE FROM brands WHERE id = '{brand_id}'")
    # Commit
    db.table('aeo_mentions').delete().eq('brand_id', brand_id).execute()
    db.table('brands').delete().eq('id', brand_id).execute()
    print('Committed deletes for Maui Real Estate.')
