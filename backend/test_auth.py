import asyncio
from dotenv import load_dotenv
from app.database import get_supabase
from app.dependencies import _hash_key
import os

load_dotenv()
async def run():
    db = get_supabase()
    raw_key = "gk_devprefix_devsecretkey123456789"
    key_hash = _hash_key(raw_key)
    print("KEY HASH:", key_hash)
    
    result = db.table("api_keys").select("*, workspaces(*)").eq("key_hash", key_hash).eq("revoked", False).maybe_single().execute()
    print("RESULT:", result)

asyncio.run(run())
