-- People Help MVP schema for Supabase (Postgres + pgvector)
-- Run this once in Supabase SQL Editor.

-- Enable pgvector extension (Supabase Cloud supports this)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents: source content for RAG (policy/process docs)
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  content text NOT NULL,
  source_url text,
  created_at timestamptz DEFAULT now()
);

-- Document chunks with embeddings (for vector search)
CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
  content text NOT NULL,
  embedding vector(1536),
  chunk_index int NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

-- No vector index for small datasets — exact scan is fast and accurate.
-- For 1000+ chunks, add: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);

-- Questions: log of user questions (for analytics and feedback)
CREATE TABLE IF NOT EXISTS questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query text NOT NULL,
  answer_text text,
  sources_json jsonb,
  created_at timestamptz DEFAULT now()
);

-- Feedback: helpful / not helpful
CREATE TABLE IF NOT EXISTS feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid REFERENCES questions(id) ON DELETE SET NULL,
  helpful boolean NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_question_id ON feedback(question_id);

-- Cases: created from Front Door when intent is create_case
CREATE TABLE IF NOT EXISTS cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject text,
  description text,
  status text NOT NULL DEFAULT 'open',
  created_at timestamptz DEFAULT now()
);

-- Workflow runs: e.g. onboarding checklist (Offer -> Day 1)
CREATE TABLE IF NOT EXISTS workflow_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_type text NOT NULL DEFAULT 'onboarding',
  status text NOT NULL DEFAULT 'in_progress',
  payload jsonb,
  created_at timestamptz DEFAULT now()
);

-- Checklist items for a workflow run
CREATE TABLE IF NOT EXISTS workflow_checklist (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_run_id uuid REFERENCES workflow_runs(id) ON DELETE CASCADE,
  label text NOT NULL,
  done boolean NOT NULL DEFAULT false,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_checklist_run ON workflow_checklist(workflow_run_id);

-- Events: integration log (mock events; later real webhooks)
CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type text NOT NULL,
  payload jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);

-- Conversations: multi-turn chat sessions
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now()
);

-- Conversation messages: individual turns in a conversation
CREATE TABLE IF NOT EXISTS conversation_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid REFERENCES conversations(id) ON DELETE CASCADE,
  role text NOT NULL,  -- 'user' | 'assistant' | 'tool'
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conv ON conversation_messages(conversation_id);

-- Workflow definitions: configurable multi-step workflow templates
CREATE TABLE IF NOT EXISTS workflow_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  definition jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Approvals: individual approval steps within a workflow run
CREATE TABLE IF NOT EXISTS approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_run_id uuid REFERENCES workflow_runs(id) ON DELETE CASCADE,
  step_name text NOT NULL,
  step_order int NOT NULL DEFAULT 0,
  approver_role text NOT NULL,
  status text NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
  decided_by text,
  notes text,
  decided_at timestamptz,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

-- Connectors: integration health tracking
CREATE TABLE IF NOT EXISTS connectors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  label text,
  type text,          -- 'hris' | 'ats' | 'messaging' | 'identity'
  status text NOT NULL DEFAULT 'not_configured',  -- 'connected' | 'error' | 'not_configured'
  last_event_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- RPC: similarity search for RAG (call from app with query embedding)
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5
)
RETURNS TABLE (id uuid, document_id uuid, content text, chunk_index int, similarity float)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  WHERE dc.embedding IS NOT NULL
    AND (1 - (dc.embedding <=> query_embedding)) > match_threshold
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
