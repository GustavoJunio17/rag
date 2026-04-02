-- ============================================================
-- Schema: Pipeline de Ingestão — IA para Gestores
-- Banco: PostgreSQL 16 + pgvector
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. Registro de documentos ingeridos
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    namespace       VARCHAR(100) NOT NULL,     -- multi-tenancy (empresa/gestor)
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(10)  NOT NULL,     -- pdf, docx, xlsx, csv, txt
    blob_path       TEXT,                      -- caminho no storage original
    metadata        JSONB DEFAULT '{}',        -- metadados extras (autor, data, etc.)
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    status          VARCHAR(20) DEFAULT 'processing'  -- processing, completed, failed
);

CREATE INDEX idx_documents_namespace ON documents(namespace);

-- ------------------------------------------------------------
-- 2. Chunks pai (texto completo para enviar ao LLM)
-- Corresponde ao "doc_chunks" do diagrama
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doc_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    namespace       VARCHAR(100) NOT NULL,
    chunk_index     INTEGER NOT NULL,          -- ordem no documento
    content         TEXT NOT NULL,             -- texto completo do chunk pai
    metadata        JSONB DEFAULT '{}',        -- página, seção, etc.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doc_chunks_namespace ON doc_chunks(namespace);
CREATE INDEX idx_doc_chunks_document ON doc_chunks(document_id);

-- ------------------------------------------------------------
-- 3. Embeddings dos chunks filho (busca vetorial)
-- Corresponde ao "doc_chunk_embeddings" do diagrama
-- O chunk filho aponta para o chunk pai via parent_chunk_id
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doc_chunk_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_chunk_id UUID NOT NULL REFERENCES doc_chunks(id) ON DELETE CASCADE,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    namespace       VARCHAR(100) NOT NULL,
    content         TEXT NOT NULL,             -- texto do chunk filho
    embedding       vector(3072),              -- vetor do embedding (Gemini embedding 2 preview)
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para busca vetorial rápida
CREATE INDEX idx_embeddings_hnsw
    ON doc_chunk_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_embeddings_namespace ON doc_chunk_embeddings(namespace);

-- ------------------------------------------------------------
-- 4. Fontes estruturadas (Excel/CSV)
-- Corresponde ao "structured_sources" do diagrama
-- Guarda schema + sample para o LLM entender a planilha
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS structured_sources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    namespace       VARCHAR(100) NOT NULL,
    sheet_name      VARCHAR(200),             -- nome da aba (Excel)
    column_schema   JSONB NOT NULL,           -- {col_name: dtype, ...}
    sample_rows     JSONB NOT NULL,           -- primeiras 20 linhas como JSON
    row_count       INTEGER,
    parquet_path    TEXT,                      -- caminho do .parquet para queries
    description     TEXT,                     -- descrição gerada por LLM (opcional)
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_structured_namespace ON structured_sources(namespace);

-- ------------------------------------------------------------
-- 5. View útil: busca vetorial com filtro por namespace
-- Use em queries do tipo:
--   SELECT * FROM search_similar('namespace', query_embedding, 10)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_similar(
    p_namespace VARCHAR,
    p_query_embedding vector(3072),
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    chunk_id        UUID,
    parent_chunk_id UUID,
    child_content   TEXT,
    parent_content  TEXT,
    similarity      FLOAT,
    metadata        JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id AS chunk_id,
        e.parent_chunk_id,
        e.content AS child_content,
        pc.content AS parent_content,
        1 - (e.embedding <=> p_query_embedding) AS similarity,
        pc.metadata
    FROM doc_chunk_embeddings e
    JOIN doc_chunks pc ON pc.id = e.parent_chunk_id
    WHERE e.namespace = p_namespace
    ORDER BY e.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
