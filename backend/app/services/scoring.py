"""
Grayn AEO — Scoring & Analytics Service

Computes all BRD-defined metrics from raw run/mention/citation data:
  • Visibility % (SC-01)
  • Week-over-week delta (SC-02)
  • Per-engine breakdown (SC-03)
  • Share of Voice (SC-04)
  • Competitor leaderboard (SC-05)
  • Average position (SC-06)
  • Citation source breakdown (SC-07)
  • Competitor sources (SC-08)
"""

import logging
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from supabase import Client
from app.models.schemas import (
    VisibilityScore,
    ShareOfVoice,
    LeaderboardEntry,
    CitationBreakdown,
    AttributeBreakdown,
    FullReport,
    WorkspaceOut,
    RunOut,
    TopLevelShareOfVoice,
    PlatformScorecardEntry,
    PlatformResponseSnippet,
    TopicPerformanceEntry,
)

logger = logging.getLogger(__name__)


def _current_iso_week() -> str:
    """Return the current ISO week string, e.g. '2026-W24'."""
    now = datetime.utcnow()
    return f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"


def _resolve_week(db: Client, workspace_id: str, iso_week: str | None) -> str:
    """
    Return the week to use for scoring.

    If the caller specifies a week, use that.  Otherwise, pick the
    most recent ISO week that has at least one *complete* run for this
    workspace.  Falls back to the current week when no data exists.
    """
    if iso_week:
        return iso_week

    current = _current_iso_week()

    # Check if current week has data
    current_runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", current)
        .eq("status", "complete")
        .limit(1)
        .execute()
        .data
        or []
    )
    if current_runs:
        return current

    # No data for this week — find the most recent week that has data
    latest = (
        db.table("aeo_runs")
        .select("iso_week")
        .eq("workspace_id", workspace_id)
        .eq("status", "complete")
        .order("iso_week", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if latest:
        return latest[0]["iso_week"]

    return current


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Visibility
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_visibility(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> VisibilityScore:
    """SC-01/02/03: Visibility %, delta, per-engine split."""
    week = _resolve_week(db, workspace_id, iso_week)

    # Derive previous week from resolved week
    from datetime import date as _date
    year, week_num = int(week[:4]), int(week.split("W")[1])
    d = _date.fromisocalendar(year, week_num, 1) - timedelta(days=7)
    prev_week = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"

    # Get all runs for this week
    runs = (
        db.table("aeo_runs")
        .select("id, engine")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )

    if not runs:
        return VisibilityScore(
            visibility_pct=0.0,
            week_over_week_delta=None,
            per_engine={},
            iso_week=week,
        )

    run_ids = [r["id"] for r in runs]

    # Get mentions for these runs where brand is target
    mentions = (
        db.table("aeo_mentions")
        .select("run_id, is_target_brand")
        .eq("workspace_id", workspace_id)
        .in_("run_id", run_ids)
        .eq("is_target_brand", True)
        .execute()
        .data
        or []
    )

    mentioned_run_ids = set(m["run_id"] for m in mentions)
    total_runs = len(runs)
    mentioned_count = len(
        set(r["id"] for r in runs if r["id"] in mentioned_run_ids)
    )
    visibility_pct = round((mentioned_count / total_runs) * 100, 1) if total_runs else 0.0

    # Per-engine breakdown
    engine_totals = defaultdict(int)
    engine_mentioned = defaultdict(int)
    for r in runs:
        engine_totals[r["engine"]] += 1
        if r["id"] in mentioned_run_ids:
            engine_mentioned[r["engine"]] += 1

    per_engine = {
        eng: round((engine_mentioned[eng] / engine_totals[eng]) * 100, 1)
        for eng in engine_totals
    }

    # Week-over-week delta
    delta = None
    prev_runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", prev_week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )
    if prev_runs:
        prev_run_ids = [r["id"] for r in prev_runs]
        prev_mentions = (
            db.table("aeo_mentions")
            .select("run_id")
            .eq("workspace_id", workspace_id)
            .in_("run_id", prev_run_ids)
            .eq("is_target_brand", True)
            .execute()
            .data
            or []
        )
        prev_mentioned = len(
            set(m["run_id"] for m in prev_mentions)
        )
        prev_pct = round((prev_mentioned / len(prev_runs)) * 100, 1)
        delta = round(visibility_pct - prev_pct, 1)

    return VisibilityScore(
        visibility_pct=visibility_pct,
        week_over_week_delta=delta,
        per_engine=per_engine,
        iso_week=week,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Share of Voice & Leaderboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_share_of_voice(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> tuple[list[ShareOfVoice], list[LeaderboardEntry]]:
    """SC-04/05/06: SoV, leaderboard, avg position."""
    week = _resolve_week(db, workspace_id, iso_week)

    runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )

    if not runs:
        return [], []

    run_ids = [r["id"] for r in runs]

    all_mentions = (
        db.table("aeo_mentions")
        .select("brand_name, position, run_id, sentiment")
        .eq("workspace_id", workspace_id)
        .in_("run_id", run_ids)
        .execute()
        .data
        or []
    )

    # Count mentions per brand
    brand_counts: dict[str, int] = defaultdict(int)
    brand_positions: dict[str, list[int]] = defaultdict(list)
    brand_runs: dict[str, set] = defaultdict(set)
    brand_sentiments: dict[str, list[str]] = defaultdict(list)

    for m in all_mentions:
        b_name = m["brand_name"]
        brand_counts[b_name] += 1
        brand_runs[b_name].add(m["run_id"])
        if m.get("position"):
            brand_positions[b_name].append(m["position"])
        if m.get("sentiment"):
            brand_sentiments[b_name].append(m["sentiment"])

    total_mentions = sum(brand_counts.values())
    total_runs = len(runs)

    sov_list = [
        ShareOfVoice(
            brand_name=name,
            mention_count=count,
            share_pct=round((count / total_mentions) * 100, 1) if total_mentions else 0,
        )
        for name, count in brand_counts.items()
    ]

    # Sort by share descending for leaderboard
    sov_list.sort(key=lambda x: x.share_pct, reverse=True)

    leaderboard = []
    for i, s in enumerate(sov_list):
        b_name = s.brand_name
        b_runs = len(brand_runs[b_name])
        visibility_pct = round((b_runs / total_runs) * 100, 1) if total_runs else 0.0
        
        avg_pos = None
        if brand_positions.get(b_name):
            avg_pos = round(sum(brand_positions[b_name]) / len(brand_positions[b_name]), 1)
            
        sentiment_val = "Neutral"
        if brand_sentiments.get(b_name):
            sentiment_val = Counter(brand_sentiments[b_name]).most_common(1)[0][0].capitalize()
            
        leaderboard.append(
            LeaderboardEntry(
                rank=i + 1,
                brand_name=b_name,
                mention_count=s.mention_count,
                share_pct=s.share_pct,
                visibility_pct=visibility_pct,
                sentiment=sentiment_val,
                avg_position=avg_pos,
            )
        )

    return sov_list, leaderboard


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Citations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_citations(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> list[CitationBreakdown]:
    """SC-07: Citation source breakdown."""
    week = _resolve_week(db, workspace_id, iso_week)

    runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )

    if not runs:
        return []

    run_ids = [r["id"] for r in runs]

    citations = (
        db.table("aeo_citations")
        .select("domain, source_type")
        .eq("workspace_id", workspace_id)
        .in_("run_id", run_ids)
        .execute()
        .data
        or []
    )

    domain_counts: dict[str, dict] = {}
    for c in citations:
        d = c["domain"]
        if d not in domain_counts:
            domain_counts[d] = {"count": 0, "source_type": c.get("source_type")}
        domain_counts[d]["count"] += 1

    # Get workspace domain to flag brand citations
    ws = (
        db.table("workspaces")
        .select("domain")
        .eq("id", workspace_id)
        .single()
        .execute()
        .data
    )
    brand_domain = ws["domain"] if ws else ""

    return [
        CitationBreakdown(
            domain=d,
            count=info["count"],
            source_type=info.get("source_type"),
            is_brand_citation=(brand_domain in d),
        )
        for d, info in sorted(
            domain_counts.items(), key=lambda x: x[1]["count"], reverse=True
        )
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Competitor Sources
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_competitor_sources(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> dict:
    """SC-08: Domains/URLs AI cites for each competitor."""
    week = _resolve_week(db, workspace_id, iso_week)

    runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )

    if not runs:
        return {}

    run_ids = [r["id"] for r in runs]

    # Get competitor mentions to find which runs have competitors
    comp_mentions = (
        db.table("aeo_mentions")
        .select("run_id, brand_name")
        .eq("workspace_id", workspace_id)
        .in_("run_id", run_ids)
        .eq("is_target_brand", False)
        .execute()
        .data
        or []
    )

    # Group run_ids by competitor brand
    comp_run_ids: dict[str, set] = defaultdict(set)
    for m in comp_mentions:
        comp_run_ids[m["brand_name"]].add(m["run_id"])

    result = {}
    for comp_name, c_run_ids in comp_run_ids.items():
        citations = (
            db.table("aeo_citations")
            .select("url, domain, source_type")
            .eq("workspace_id", workspace_id)
            .in_("run_id", list(c_run_ids))
            .execute()
            .data
            or []
        )
        
        domain_counts = defaultdict(int)
        for c in citations:
            domain_counts[c["domain"]] += 1
            
        agg = [{"domain": dom, "count": cnt} for dom, cnt in domain_counts.items()]
        agg.sort(key=lambda x: x["count"], reverse=True)
        result[comp_name] = agg[:10]

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Attribute Breakdown
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_attribute_breakdown(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> list[AttributeBreakdown]:
    """SC-09: Tally up attributes assigned to the brand and aggregate sentiment."""
    week = _resolve_week(db, workspace_id, iso_week)

    runs = (
        db.table("aeo_runs")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("iso_week", week)
        .eq("status", "complete")
        .execute()
        .data
        or []
    )

    if not runs:
        return []

    run_ids = [r["id"] for r in runs]

    mentions = (
        db.table("aeo_mentions")
        .select("attributes")
        .eq("workspace_id", workspace_id)
        .in_("run_id", run_ids)
        .eq("is_target_brand", True)
        .execute()
        .data
        or []
    )

    attr_stats = defaultdict(lambda: {"total": 0, "positive": 0})

    for m in mentions:
        attributes = m.get("attributes") or []
        for attr in attributes:
            name = attr.get("name")
            if not name:
                continue
            sentiment = attr.get("sentiment", "neutral")
            attr_stats[name]["total"] += 1
            if sentiment == "positive":
                attr_stats[name]["positive"] += 1

    result = []
    for name, stats in attr_stats.items():
        total = stats["total"]
        positive = stats["positive"]
        pos_pct = round((positive / total) * 100, 1) if total else 0.0
        overall_sentiment = "positive" if pos_pct >= 50 else "negative"
        
        result.append(
            AttributeBreakdown(
                attribute=name,
                positive_pct=pos_pct,
                sentiment=overall_sentiment,
            )
        )

    # Sort by total mentions of that attribute
    result.sort(key=lambda x: attr_stats[x.attribute]["total"], reverse=True)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Platform Scorecard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_platform_scorecard(
    db: Client, workspace_id: str, week: str, target_brand_domain: str, top_competitor: str | None
) -> list[PlatformScorecardEntry]:
    """SC-11: Visibility per engine compared to the top competitor."""
    runs = db.table("aeo_runs").select("id, engine, raw_response, created_at, prompt_id").eq("workspace_id", workspace_id).eq("iso_week", week).eq("status", "complete").execute().data or []
    if not runs:
        return []

    prompt_ids = list(set([r["prompt_id"] for r in runs if r.get("prompt_id")]))
    prompts = db.table("aeo_prompts").select("id, prompt_text").in_("id", prompt_ids).execute().data or [] if prompt_ids else []
    prompt_map = {p["id"]: p["prompt_text"] for p in prompts}

    mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").eq("workspace_id", workspace_id).in_("run_id", [r["id"] for r in runs]).execute().data or []

    engine_totals = defaultdict(int)
    for r in runs:
        engine_totals[r["engine"]] += 1

    target_engine_hits = defaultdict(set)
    comp_engine_hits = defaultdict(set)

    run_to_engine = {r["id"]: r["engine"] for r in runs}

    for m in mentions:
        eng = run_to_engine.get(m["run_id"])
        if not eng: continue
        if m["is_target_brand"]:
            target_engine_hits[eng].add(m["run_id"])
        elif top_competitor and m["brand_name"] == top_competitor:
            comp_engine_hits[eng].add(m["run_id"])

    scorecard = []
    for eng, total in engine_totals.items():
        if total == 0: continue
        target_vis = round((len(target_engine_hits[eng]) / total) * 100, 1)
        comp_vis = round((len(comp_engine_hits[eng]) / total) * 100, 1)
        gap = round(target_vis - comp_vis, 1)
        status = "Leading" if gap >= 5 else "Behind" if gap <= -5 else "Close"
        
        scorecard.append(
            PlatformScorecardEntry(
                platform=eng.replace("_", " ").title() if eng != "openai" else "ChatGPT",
                your_visibility=target_vis,
                top_competitor=top_competitor or "N/A",
                top_competitor_visibility=comp_vis,
                gap=gap,
                status=status
            )
        )
    return scorecard


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Topic Performance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_topic_performance(
    db: Client, workspace_id: str, week: str, top_competitor: str | None
) -> list[TopicPerformanceEntry]:
    """SC-12: Visibility per topic compared to the top competitor."""
    runs = db.table("aeo_runs").select("id, prompt_id").eq("workspace_id", workspace_id).eq("iso_week", week).eq("status", "complete").execute().data or []
    if not runs:
        return []

    prompts = db.table("aeo_prompts").select("id, prompt_text").eq("workspace_id", workspace_id).in_("id", [r["prompt_id"] for r in runs if r.get("prompt_id")]).execute().data or []
    prompt_map = {p["id"]: p["prompt_text"] for p in prompts}

    mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").eq("workspace_id", workspace_id).in_("run_id", [r["id"] for r in runs]).execute().data or []

    prompt_totals = defaultdict(int)
    for r in runs:
        if r.get("prompt_id"):
            prompt_totals[r["prompt_id"]] += 1

    target_prompt_hits = defaultdict(set)
    comp_prompt_hits = defaultdict(set)

    run_to_prompt = {r["id"]: r.get("prompt_id") for r in runs}

    for m in mentions:
        pid = run_to_prompt.get(m["run_id"])
        if not pid: continue
        if m["is_target_brand"]:
            target_prompt_hits[pid].add(m["run_id"])
        elif top_competitor and m["brand_name"] == top_competitor:
            comp_prompt_hits[pid].add(m["run_id"])

    performance = []
    for pid, total in prompt_totals.items():
        if total == 0: continue
        text = prompt_map.get(pid, "Unknown Query")
        target_vis = round((len(target_prompt_hits[pid]) / total) * 100, 1)
        comp_vis = round((len(comp_prompt_hits[pid]) / total) * 100, 1)
        gap = target_vis - comp_vis
        status = "Leading" if gap >= 5 else "Behind" if gap <= -5 else "Close"
        
        performance.append(
            TopicPerformanceEntry(
                topic=text,
                your_visibility=target_vis,
                top_competitor=top_competitor or "N/A",
                top_competitor_visibility=comp_vis,
                status=status
            )
        )
    return performance


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Historical Trend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_historical_trend(
    db: Client, workspace_id: str, weeks: int = 6
) -> list[dict]:
    """Calculates weekly visibility trend for the target brand and top competitors."""
    now = datetime.utcnow()
    # Generate the last N weeks
    iso_weeks = []
    for i in range(weeks):
        d = now - timedelta(weeks=i)
        iso_weeks.append(f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}")
    iso_weeks.reverse() # Oldest to newest

    trend_data = []
    
    ws = db.table("workspaces").select("brand_name", "domain", "aliases").eq("id", workspace_id).single().execute().data
    target_lower = ws.get("brand_name", "").lower()
    
    for w in iso_weeks:
        runs = db.table("aeo_runs").select("id").eq("workspace_id", workspace_id).eq("iso_week", w).eq("status", "complete").execute().data or []
        if not runs:
            trend_data.append({"week": w, "visibility": 0.0})
            continue

        run_ids = [r["id"] for r in runs]
        mentions = db.table("aeo_mentions").select("run_id, brand_name, is_target_brand").eq("workspace_id", workspace_id).in_("run_id", run_ids).execute().data or []
        
        target_hits = set()
        for m in mentions:
            if m["is_target_brand"]:
                target_hits.add(m["run_id"])
        
        vis_pct = round((len(target_hits) / len(runs)) * 100, 1) if runs else 0.0
        trend_data.append({"week": w, "visibility": vis_pct})
        
    return trend_data

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Full Report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def build_full_report(
    db: Client, workspace_id: str, iso_week: str | None = None
) -> FullReport:
    """SC-10: Composite report combining all metrics."""
    week = _resolve_week(db, workspace_id, iso_week)

    ws = (
        db.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .single()
        .execute()
        .data
    )

    visibility = compute_visibility(db, workspace_id, week)
    sov_list, leaderboard = compute_share_of_voice(db, workspace_id, week)
    citations = compute_citations(db, workspace_id, week)
    comp_sources = compute_competitor_sources(db, workspace_id, week)
    attribute_breakdown = compute_attribute_breakdown(db, workspace_id, week)

    top_competitor = None
    # Skip index 0 if it's the target brand, though 'Leaderboard' usually doesn't include the target brand if is_target_brand logic is applied?
    # Wait, all_mentions includes target brand right now! The target brand is part of the leaderboard in OpenLens.
    # The target brand is the workspace brand. So top competitor is the first one that is NOT the workspace brand.
    for entry in leaderboard:
        if ws["domain"] not in entry.brand_name.lower() and ws["brand_name"].lower() not in entry.brand_name.lower():
            top_competitor = entry.brand_name
            break

    platform_scorecard = compute_platform_scorecard(db, workspace_id, week, ws.get("domain", ""), top_competitor)
    topic_performance = compute_topic_performance(db, workspace_id, week, top_competitor)

    recent_runs_data = (
        db.table("aeo_runs")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
        .data
        or []
    )
    recent_runs = []
    for r in recent_runs_data:
        if r.get("status") == "error":
            # Extract basic error string if raw_response exists
            r["error_message"] = r.get("raw_response", "Unknown error")
        recent_runs.append(RunOut(**r))

    # Find top level share of voice for the target brand
    target_lower = ws.get("brand_name", "").lower()
    top_level_sov = None
    for entry in leaderboard:
        if target_lower in entry.brand_name.lower():
            from app.models.schemas import TopLevelShareOfVoice
            top_level_sov = TopLevelShareOfVoice(
                share_pct=entry.share_pct,
                avg_position=entry.avg_position or 1.0
            )
            break

    from app.services.insights import generate_report_insight

    report_dump = {
        "workspace": ws,
        "visibility": visibility.model_dump(),
        "leaderboard": [l.model_dump() for l in leaderboard[:5]],
        "platform_scorecard": [p.model_dump() for p in platform_scorecard],
        "topic_performance": [t.model_dump() for t in topic_performance[:3]],
    }
    
    ai_insight = await generate_report_insight(report_dump)

    return FullReport(
        workspace=WorkspaceOut(**ws),
        visibility=visibility,
        share_of_voice=top_level_sov,
        leaderboard=leaderboard,
        brand_citations=citations,
        competitor_sources=comp_sources,
        attribute_breakdown=attribute_breakdown,
        platform_scorecard=platform_scorecard,
        topic_performance=topic_performance,
        recent_runs=recent_runs,
        iso_week=week,
        ai_insight=ai_insight,
    )
