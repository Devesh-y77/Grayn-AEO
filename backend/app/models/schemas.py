"""
Grayn AEO — Pydantic Schemas

Request/response models for the REST API.
Organised by domain: workspace, prompts, competitors, runs,
analytics, content, slack, and admin.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EngineType(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GOOGLE_AI = "google_ai"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    GROK = "grok"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Intent(str, Enum):
    CATEGORY = "category"
    COMPARISON = "comparison"
    PROBLEM = "problem"
    EVALUATIVE = "evaluative"


class Persona(str, Enum):
    EXEC = "exec"
    SEO = "seo"


class RefillAction(str, Enum):
    WRITE_NEW = "write-new"
    REFRESH = "refresh"
    EXPAND = "expand"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Workspace
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkspaceOut(BaseModel):
    id: str
    brand_name: str
    domain: str
    aliases: Optional[List[str]] = None
    brand_context: Optional[str] = None
    target_location: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkspaceCreate(BaseModel):
    brand_name: str
    domain: str
    aliases: Optional[List[str]] = None
    brand_context: Optional[str] = None
    target_location: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API Key
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ApiKeyOut(BaseModel):
    id: str
    key_prefix: str
    revoked: bool
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApiKeyCreated(BaseModel):
    """Returned only once when a key is minted."""
    id: str
    key_prefix: str
    raw_key: str = Field(
        ..., description="Full API key — shown once, never stored."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Prompts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PromptCreate(BaseModel):
    prompt_text: str
    intent: Optional[Intent] = None
    persona: Optional[Persona] = None
    topic_cluster: Optional[str] = None
    attributes: Optional[List[str]] = Field(default_factory=list)


class PromptOut(BaseModel):
    id: str
    workspace_id: str
    prompt_text: str
    intent: Optional[str] = None
    persona: Optional[str] = None
    topic_cluster: Optional[str] = None
    attributes: Optional[List[str]] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None


class PromptBulkCreate(BaseModel):
    prompts: List[PromptCreate]


class PromptSeed(BaseModel):
    topics: List[str]
    count_per_topic: int = Field(default=5, ge=1, le=20)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Competitors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CompetitorCreate(BaseModel):
    brand_name: str
    domain: str
    aliases: Optional[List[str]] = None


class CompetitorOut(BaseModel):
    id: str
    workspace_id: str
    brand_name: str
    domain: str
    aliases: Optional[List[str]] = None
    created_at: Optional[datetime] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Workstreams
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkstreamCreate(BaseModel):
    name: str
    topics: Optional[List[str]] = Field(default_factory=list)
    attribute_filters: Optional[List[str]] = Field(default_factory=list)
    target_visibility: Optional[float] = 0.0


class WorkstreamOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    topics: Optional[List[str]] = Field(default_factory=list)
    attribute_filters: Optional[List[str]] = Field(default_factory=list)
    target_visibility: Optional[float] = 0.0
    created_at: Optional[datetime] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Runs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RunTrigger(BaseModel):
    engines: Optional[List[EngineType]] = None
    prompt_ids: Optional[List[str]] = None


class RunOut(BaseModel):
    id: str
    workspace_id: str
    prompt_id: str
    engine: str
    iso_week: str
    status: str
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class RunLogItem(BaseModel):
    engine: str
    prompt_text: str
    status: str
    created_at: Optional[datetime] = None

class RunStatus(BaseModel):
    progress_pct: float
    completed: int
    total: int
    is_running: bool
    latest_logs: List[RunLogItem] = Field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Mentions & Citations (Judge output)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AttributeData(BaseModel):
    name: str
    sentiment: Sentiment
    competitor: Optional[str] = None

class MentionData(BaseModel):
    brand_name: str
    is_target_brand: bool
    position: int
    sentiment: Sentiment
    attributes: List[AttributeData] = Field(default_factory=list)


class CitationData(BaseModel):
    url: str
    domain: str
    source_type: str


class JudgeExtraction(BaseModel):
    """Structured output the Anthropic judge returns."""
    mentions: List[MentionData]
    citations: List[CitationData]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Analytics / Scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class VisibilityScore(BaseModel):
    visibility_pct: float
    week_over_week_delta: Optional[float] = None
    per_engine: dict = {}
    iso_week: str


class ShareOfVoice(BaseModel):
    brand_name: str
    mention_count: int
    share_pct: float


class LeaderboardEntry(BaseModel):
    rank: int
    brand_name: str
    mention_count: int
    share_pct: float
    visibility_pct: float = 0.0
    sentiment: Optional[str] = None
    avg_position: Optional[float] = None


class PlatformResponseSnippet(BaseModel):
    date: str
    query: str
    is_mentioned: bool
    raw_text: str

class PlatformScorecardEntry(BaseModel):
    platform: str
    your_visibility: float
    top_competitor: str
    top_competitor_visibility: float
    gap: float
    status: str
    recent_responses: List[PlatformResponseSnippet] = Field(default_factory=list)


class TopicPerformanceEntry(BaseModel):
    topic: str
    your_visibility: float
    top_competitor: str
    top_competitor_visibility: float
    status: str


class CitationBreakdown(BaseModel):
    domain: str
    count: int
    source_type: Optional[str] = None
    is_brand_citation: bool = False
    urls: List[dict] = []  # Added for frontend accordion


class AttributeBreakdown(BaseModel):
    attribute: str
    positive_pct: float
    sentiment: str


class PlatformResponseSnippet(BaseModel):
    date: str
    query: str
    is_mentioned: bool
    raw_text: str


class PlatformScorecardEntry(BaseModel):
    platform: str
    your_visibility: float
    top_competitor: str
    top_competitor_visibility: float
    status: str
    recent_responses: List[PlatformResponseSnippet] = []


class TrackerResponseSnippet(BaseModel):
    engine: str
    timestamp: str
    prompt_text: str
    raw_text: str


class QueryDataTrackerResponse(BaseModel):
    prompt_id: str
    prompt_text: str
    insight_log: str
    responses: List[TrackerResponseSnippet]


class TopLevelShareOfVoice(BaseModel):
    share_pct: float
    avg_position: float


class FullReport(BaseModel):
    workspace: WorkspaceOut
    visibility: VisibilityScore
    share_of_voice: Optional[TopLevelShareOfVoice] = None
    leaderboard: List[LeaderboardEntry]
    brand_citations: List[CitationBreakdown]
    competitor_sources: dict = {}
    attribute_breakdown: List[AttributeBreakdown] = Field(default_factory=list)
    platform_scorecard: List[PlatformScorecardEntry] = Field(default_factory=list)
    topic_performance: List[TopicPerformanceEntry] = Field(default_factory=list)
    recent_runs: List[RunOut] = Field(default_factory=list)
    iso_week: str
    ai_insight: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Content Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ClusterOut(BaseModel):
    id: str
    workspace_id: str
    cluster_name: str
    search_volume: Optional[int] = None
    brand_ai_visibility: Optional[float] = None
    opportunity_score: Optional[float] = None
    refill_action: Optional[str] = None
    created_at: Optional[datetime] = None


class ContentBrief(BaseModel):
    cluster_id: str
    cluster_name: str
    target_queries: List[str]
    outline: List[str]
    sources_to_win: List[str]
    refill_action: str


class ContentDraft(BaseModel):
    cluster_id: str
    cluster_name: str
    title: str
    body: str


class Recommendation(BaseModel):
    cluster_id: str
    cluster_name: str
    action: str
    impact_score: float
    target_queries: List[str]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Discovery / Onboarding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DiscoverRequest(BaseModel):
    url: str
    num_queries: Optional[int] = 5
    target_location: Optional[str] = None


class SuggestedQuery(BaseModel):
    text: str
    attributes: List[str] = Field(default_factory=list)


class DiscoverResult(BaseModel):
    brand_name: Optional[str] = None
    suggested_competitors: List[CompetitorCreate]
    suggested_queries: List[SuggestedQuery]
    themes: List[str]


class DiscoverApply(BaseModel):
    competitors: List[CompetitorCreate]
    queries: List[SuggestedQuery]
    engines: List[EngineType] = Field(default_factory=list)
    target_location: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Slack
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SlackQuery(BaseModel):
    question: str
    persona: Optional[Persona] = Persona.EXEC


class SlackPayload(BaseModel):
    blocks: list
    text: str  # Fallback plain text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Alerts & Digests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AlertOut(BaseModel):
    type: str
    message: str
    severity: str
    created_at: Optional[datetime] = None


class DigestOut(BaseModel):
    id: str
    workspace_id: str
    period_week: str
    payload: dict
    created_at: Optional[datetime] = None
