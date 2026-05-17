CREATE TABLE IF NOT EXISTS portfolio_rag_documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES organizations(id),
  source_type  TEXT NOT NULL CHECK (source_type IN ('initiative','milestone','kpi','risk')),
  source_id    UUID NOT NULL,
  title        TEXT NOT NULL,
  content      TEXT NOT NULL,
  search_text  TEXT NOT NULL,
  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, source_type, source_id)
);

CREATE INDEX IF NOT EXISTS portfolio_rag_documents_tenant_idx
  ON portfolio_rag_documents(tenant_id, source_type);

ALTER TABLE portfolio_rag_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "portfolio_rag_documents_select" ON portfolio_rag_documents;
CREATE POLICY "portfolio_rag_documents_select"
  ON portfolio_rag_documents FOR SELECT
  USING (tenant_id = current_tenant_id());

DROP POLICY IF EXISTS "portfolio_rag_documents_insert" ON portfolio_rag_documents;
CREATE POLICY "portfolio_rag_documents_insert"
  ON portfolio_rag_documents FOR INSERT
  WITH CHECK (tenant_id = current_tenant_id());

DROP POLICY IF EXISTS "portfolio_rag_documents_update" ON portfolio_rag_documents;
CREATE POLICY "portfolio_rag_documents_update"
  ON portfolio_rag_documents FOR UPDATE
  USING (tenant_id = current_tenant_id())
  WITH CHECK (tenant_id = current_tenant_id());

DROP POLICY IF EXISTS "portfolio_rag_documents_delete" ON portfolio_rag_documents;
CREATE POLICY "portfolio_rag_documents_delete"
  ON portfolio_rag_documents FOR DELETE
  USING (tenant_id = current_tenant_id());
