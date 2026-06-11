"""
Grayn AEO — Tracking Engine

Orchestrates the full reactive pipeline:
  1. Query AI engines (real or mock)
  2. Run the Anthropic judge for extraction
  3. Persist runs, mentions, and citations

Supports idempotent weekly runs (TR-07), manual triggers (TR-08),
per-run cost capture (TR-09), and resilient batch processing (TR-10).
"""

import logging
from datetime import datetime
from supabase import Client
from app.models.schemas import EngineType
from app.services.providers.base import get_provider
from app.services.judge import extract_mentions_and_citations

logger = logging.getLogger(__name__)


def _current_iso_week() -> str:
    now = datetime.utcnow()
    return f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"


async def run_single_prompt(
    db: Client,
    workspace: dict,
    prompt: dict,
    engine: EngineType,
    iso_week: str | None = None,
) -> dict | None:
    """
    Execute one prompt × engine × week.

    Returns the created run row, or None if the run already exists
    (idempotent) or if the engine fails (resilient).
    """
    week = iso_week or _current_iso_week()
    workspace_id = workspace["id"]
    prompt_id = prompt["id"]

    # ── Idempotency check (TR-07) ────────────────────────
    existing = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("prompt_id", prompt_id)
        .eq("engine", engine.value)
        .eq("iso_week", week)
        .maybe_single()
        .execute()
    )
    if existing is not None and existing.data:
        logger.info(
            "Run already exists for prompt=%s engine=%s week=%s — skipping",
            prompt_id, engine.value, week,
        )
        return existing.data

    # ── Query the engine ─────────────────────────────────
    try:
        provider = get_provider(engine)
        if hasattr(provider, "__aenter__"):
            async with provider as p:
                result = await p.query(prompt["prompt_text"])
        else:
            result = await provider.query(prompt["prompt_text"])
    except Exception as exc:
        logger.error(
            "Engine %s failed for prompt %s: %s", engine.value, prompt_id, exc
        )
        # Persist a failed run (TR-10)
        failed_run = (
            db.table("aeo_runs")
            .insert({
                "workspace_id": workspace_id,
                "prompt_id": prompt_id,
                "engine": engine.value,
                "iso_week": week,
                "raw_response": str(exc),
                "status": "error",
                "cost_usd": 0,
            })
            .execute()
        )
        return failed_run.data[0] if failed_run.data else None

    # ── Run the judge ────────────────────────────────────
    try:
        target_brand = workspace.get("brand_name", "TargetBrand")
        brand_aliases = workspace.get("aliases", [])
        extraction = await extract_mentions_and_citations(
            answer_text=result.raw_text,
            target_brand=target_brand,
            brand_aliases=brand_aliases,
        )
    except Exception as exc:
        logger.error("Judge failed for prompt %s: %s", prompt_id, exc)
        failed_run = (
            db.table("aeo_runs")
            .insert({
                "workspace_id": workspace_id,
                "prompt_id": prompt_id,
                "engine": engine.value,
                "iso_week": week,
                "raw_response": f"Judge extraction failed: {exc}\n\nRaw answer:\n{result.raw_text}",
                "status": "error",
                "cost_usd": result.cost_usd,
            })
            .execute()
        )
        return failed_run.data[0] if failed_run.data else None

    # ── Persist run ──────────────────────────────────────
    run_data = {
        "workspace_id": workspace_id,
        "prompt_id": prompt_id,
        "engine": engine.value,
        "iso_week": week,
        "raw_response": result.raw_text,
        "parsed_response": (
            extraction.model_dump() if extraction else None
        ),
        "cost_usd": result.cost_usd,
        "status": "complete",
    }
    run_row = db.table("aeo_runs").insert(run_data).execute()
    run_id = run_row.data[0]["id"]

    # ── Persist mentions & citations ─────────────────────
    if extraction:
        import json
        target_lower = workspace.get("brand_name", "").lower()
        aliases = [a.lower() for a in (workspace.get("aliases") or [])]
        
        for m in extraction.mentions:
            m_lower = m.brand_name.lower()
            if m_lower == target_lower or m_lower in aliases:
                m.is_target_brand = True
            
            attrs_dump = [a.model_dump() for a in m.attributes]
            db.table("aeo_mentions").insert({
                "workspace_id": workspace_id,
                "run_id": run_id,
                "brand_name": m.brand_name,
                "is_target_brand": m.is_target_brand,
                "position": m.position,
                "sentiment": m.sentiment.value,
                "attributes": attrs_dump,
            }).execute()

        for c in extraction.citations:
            db.table("aeo_citations").insert({
                "workspace_id": workspace_id,
                "run_id": run_id,
                "url": c.url,
                "domain": c.domain,
                "source_type": c.source_type,
            }).execute()

    logger.info(
        "Completed run: prompt=%s engine=%s cost=$%.4f mentions=%d citations=%d",
        prompt_id,
        engine.value,
        result.cost_usd,
        len(extraction.mentions) if extraction else 0,
        len(extraction.citations) if extraction else 0,
    )
    return run_row.data[0]


async def trigger_batch_run(
    db: Client,
    workspace: dict,
    engines_filter: list[EngineType] | None = None,
    prompt_ids: list[str] | None = None,
) -> dict:
    """
    Run the full tracking batch for a workspace.

    Processes every active prompt × every engine (or a filtered subset).
    Failed individual runs are logged and skipped (TR-10).
    """
    workspace_id = workspace["id"]
    iso_week = _current_iso_week()

    # Get prompts
    query = (
        db.table("aeo_prompts")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("is_active", True)
    )
    if prompt_ids:
        query = query.in_("id", prompt_ids)

    prompts = query.execute().data or []

    engines = engines_filter if engines_filter else list(EngineType)

    results = {"completed": 0, "skipped": 0, "failed": 0, "total_cost": 0.0}

    for prompt in prompts:
        for engine in engines:
            try:
                run = await run_single_prompt(
                    db, workspace, prompt, engine, iso_week
                )
                if run and run.get("status") == "complete":
                    results["completed"] += 1
                    results["total_cost"] += run.get("cost_usd", 0) or 0
                elif run and run.get("status") == "error":
                    results["failed"] += 1
                else:
                    results["skipped"] += 1
            except Exception as exc:
                logger.error("Batch run error: %s", exc)
                results["failed"] += 1

    results["total_cost"] = round(results["total_cost"], 4)
    results["iso_week"] = iso_week
    return results
