-- create_reports_table.sql
CREATE TABLE IF NOT EXISTS public.aeo_reports (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id uuid REFERENCES public.workspaces(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    report_data jsonb NOT NULL
);
