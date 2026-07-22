-- Grayn AEO Supabase Schema

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Workspace
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    aliases TEXT[],
    brand_context TEXT,
    target_location TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 1.5 Brands
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    canonical_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 2. API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    revoked BOOLEAN DEFAULT false,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 3. Prompts
CREATE TABLE aeo_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    intent TEXT,
    persona TEXT,
    topic_cluster TEXT,
    embedding VECTOR(1536),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    UNIQUE(workspace_id, prompt_text)
);

-- 4. Competitors
CREATE TABLE aeo_competitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    brand_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    aliases TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 5. Runs
CREATE TABLE aeo_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES aeo_prompts(id) ON DELETE CASCADE,
    engine TEXT NOT NULL,
    iso_week TEXT NOT NULL, -- e.g. "2026-W24"
    raw_response TEXT,
    parsed_response JSONB,
    cost_usd NUMERIC(10, 6),
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    pass_number INT DEFAULT 1,
    scan_group_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_aeo_runs_scan_group ON aeo_runs(scan_group_id);

-- 6. Mentions
CREATE TABLE aeo_mentions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    run_id UUID REFERENCES aeo_runs(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    raw_name TEXT,
    brand_name TEXT NOT NULL,
    is_target_brand BOOLEAN DEFAULT false,
    position INTEGER,
    sentiment TEXT, -- positive, neutral, negative
    attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 7. Citations
CREATE TABLE aeo_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    run_id UUID REFERENCES aeo_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    source_type TEXT,
    source TEXT DEFAULT 'judge_extracted',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 8. Brand Content
CREATE TABLE aeo_brand_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 9. Clusters
CREATE TABLE aeo_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    cluster_name TEXT NOT NULL,
    search_volume INTEGER,
    brand_ai_visibility NUMERIC(5, 2),
    opportunity_score NUMERIC(5, 2),
    refill_action TEXT, -- write-new, refresh, expand
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 10. Keyword Volume
CREATE TABLE aeo_keyword_volumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    search_volume INTEGER,
    cpc NUMERIC(10, 2),
    competition NUMERIC(5, 2),
    difficulty NUMERIC(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 11. Digests
CREATE TABLE aeo_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    period_week TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- ---------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS)
-- ---------------------------------------------------------------------------
-- Enable RLS on all tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_competitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_mentions ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_brand_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_keyword_volumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeo_digests ENABLE ROW LEVEL SECURITY;

-- Create an Auth Role constraint. 
-- In Supabase, requests are authenticated with a JWT token.
-- We can set up a policy where the workspace_id matches current_setting('request.jwt.claims')::json->>'workspace_id'
-- However, since the FastAPI backend is communicating directly via a service key or custom API key,
-- we may handle the isolation at the application layer and use RLS to enforce it via set_config in postgres.

-- Example Policy: Application sets `app.current_workspace_id` before querying.
CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS UUID AS $$
  SELECT current_setting('app.current_workspace_id', true)::UUID;
$$ LANGUAGE SQL STABLE;

-- Workspace Policy
CREATE POLICY workspace_isolation_policy ON workspaces
    FOR ALL USING (id = current_workspace_id());

-- Policy for tables with workspace_id
CREATE POLICY workspace_isolation_policy ON brands FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON api_keys FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_prompts FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_competitors FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_runs FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_mentions FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_citations FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_brand_content FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_clusters FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_keyword_volumes FOR ALL USING (workspace_id = current_workspace_id());
CREATE POLICY workspace_isolation_policy ON aeo_digests FOR ALL USING (workspace_id = current_workspace_id());
