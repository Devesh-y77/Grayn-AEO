"""
Grayn AEO — Admin / Internal Router (/internal)

All endpoints require an X-Admin-Token header.
Used for workspace provisioning, API key management, and
operational triggers.
"""

import hashlib
import secrets
from fastapi import APIRouter, Depends
from supabase import Client
from app.database import get_supabase
from app.dependencies import require_admin
from app.config import get_settings
from app.models.schemas import (
    WorkspaceCreate,
    WorkspaceOut,
    ApiKeyOut,
    ApiKeyCreated,
)
from app.services import tracking, scoring

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_admin)],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Workspace Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/workspaces", response_model=WorkspaceOut)
def create_workspace(
    body: WorkspaceCreate,
    db: Client = Depends(get_supabase),
):
    """WS-06: Create a new workspace."""
    data = {
        "brand_name": body.brand_name,
        "domain": body.domain,
        "aliases": body.aliases,
        "brand_context": body.brand_context,
    }
    result = db.table("workspaces").insert(data).execute()
    return result.data[0]


@router.get("/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(db: Client = Depends(get_supabase)):
    """List all workspaces."""
    result = db.table("workspaces").select("*").execute()
    return result.data or []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API Key Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post(
    "/workspaces/{workspace_id}/api-keys", response_model=ApiKeyCreated
)
def mint_api_key(
    workspace_id: str,
    db: Client = Depends(get_supabase),
):
    """
    WS-04: Mint a new workspace API key.

    The full key is shown ONCE in the response and never stored.
    Only the SHA-256 hash is persisted.
    """
    # Generate key: gk_<prefix>_<secret>
    prefix = secrets.token_hex(4)   # 8 chars
    secret = secrets.token_hex(24)  # 48 chars
    raw_key = f"gk_{prefix}_{secret}"

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    data = {
        "workspace_id": workspace_id,
        "key_prefix": f"gk_{prefix}_",
        "key_hash": key_hash,
    }
    result = db.table("api_keys").insert(data).execute()
    row = result.data[0]

    return ApiKeyCreated(
        id=row["id"],
        key_prefix=row["key_prefix"],
        raw_key=raw_key,
    )


@router.get(
    "/workspaces/{workspace_id}/api-keys", response_model=list[ApiKeyOut]
)
def list_api_keys(
    workspace_id: str,
    db: Client = Depends(get_supabase),
):
    """WS-05: List API keys for a workspace (hashes hidden)."""
    result = (
        db.table("api_keys")
        .select("id, workspace_id, key_prefix, revoked, last_used_at, created_at")
        .eq("workspace_id", workspace_id)
        .execute()
    )
    return result.data or []


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    db: Client = Depends(get_supabase),
):
    """WS-05: Revoke an API key."""
    db.table("api_keys").update({"revoked": True}).eq("id", key_id).execute()
    return {"status": "revoked"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Operational Triggers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/workspaces/{workspace_id}/runs/trigger")
async def admin_trigger_runs(
    workspace_id: str,
    db: Client = Depends(get_supabase),
):
    """Admin trigger: run tracking for a workspace."""
    ws = (
        db.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .single()
        .execute()
        .data
    )
    result = await tracking.trigger_batch_run(db, ws)
    return result


@router.post("/workspaces/{workspace_id}/digest")
def create_digest(
    workspace_id: str,
    db: Client = Depends(get_supabase),
):
    """AL-02: Generate and persist a weekly digest."""
    report = scoring.build_full_report(db, workspace_id)

    digest_data = {
        "workspace_id": workspace_id,
        "period_week": report.iso_week,
        "payload": report.model_dump(),
    }
    result = db.table("aeo_digests").insert(digest_data).execute()
    return result.data[0]


@router.get("/status")
def system_status():
    """API-06: System status with provider modes."""
    settings = get_settings()
    return {
        "status": "ok",
        "mock_mode": settings.USE_MOCK_PROVIDERS,
        "providers": {
            "openai": "live" if settings.openai_available else "mock",
            "gemini": "live" if settings.gemini_available else "mock",
            "anthropic": "live" if settings.anthropic_available else "mock",
            "perplexity": "mock",
        },
    }
