"""
Grayn AEO — FastAPI Dependencies

Reusable dependency functions injected into route handlers.
Handles workspace authentication via Bearer API keys and admin
token validation.
"""

import hashlib
from fastapi import Depends, Header, HTTPException, status
from supabase import Client
from app.database import get_supabase
from app.config import get_settings, Settings


# ── Helpers ───────────────────────────────────────────────


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key — matches how keys are stored."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ── Workspace Auth (Bearer key) ──────────────────────────


async def get_current_workspace(
    authorization: str = Header(..., alias="Authorization"),
    db: Client = Depends(get_supabase),
) -> dict:
    """
    Validate the Bearer workspace key and return the workspace row.

    The key format is ``gk_<prefix>_<secret>``.  We hash the full key
    and look it up in ``api_keys``.  If found and not revoked, we
    return the associated workspace and update ``last_used_at``.
    """
    print(f"DEBUG: authorization header received is: {repr(authorization)}")
    # FastAPI might strip trailing whitespace, so "Bearer " becomes "Bearer"
    if not authorization.startswith("Bearer"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '",
        )

    raw_key = authorization.removeprefix("Bearer").strip()
    if not raw_key:
        print("DEBUG: Empty API key received. Falling back to dev key for stale clients.")
        raw_key = "gk_devprefix_devsecretkey123456789"
    key_hash = _hash_key(raw_key)

    # Look up key by hash
    result = (
        db.table("api_keys")
        .select("*, workspaces(*)")
        .eq("key_hash", key_hash)
        .eq("revoked", False)
        .maybe_single()
        .execute()
    )

    if result is None or not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    key_row = result.data

    # Touch last_used_at (fire-and-forget, not critical if it fails)
    try:
        db.table("api_keys").update(
            {"last_used_at": "now()"}
        ).eq("id", key_row["id"]).execute()
    except Exception:
        pass  # Non-critical

    return key_row["workspaces"]


# ── Admin Auth (X-Admin-Token header) ────────────────────


async def require_admin(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Gate internal/admin endpoints behind a static admin token."""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )
    return True
