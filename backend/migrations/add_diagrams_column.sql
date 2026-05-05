-- Migration: Add architecture_diagrams and repo_metadata columns to project_results
-- Run: psql -U postgres -d vibeanalytix -f migrations/add_diagrams_column.sql
-- Or apply via alembic data migration if you prefer.

ALTER TABLE project_results
    ADD COLUMN IF NOT EXISTS architecture_diagrams JSONB,
    ADD COLUMN IF NOT EXISTS repo_metadata JSONB;

-- Indices for fast JSON field access (optional but beneficial for large deployments)
CREATE INDEX IF NOT EXISTS idx_project_results_has_diagrams
    ON project_results ((architecture_diagrams IS NOT NULL));
