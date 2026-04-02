"""
Armazenamento no PostgreSQL + pgvector.
Salva doc_chunks, doc_chunk_embeddings e structured_sources.
"""

import json
import psycopg
from pgvector.psycopg import register_vector

from config import config


class PgVectorStore:
    """Interface com o banco pgvector."""

    def __init__(self):
        self.conn_string = config.database.connection_string
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.conn_string, autocommit=True)
            register_vector(self._conn)
        return self._conn

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    # ----------------------------------------------------------------
    # Documento
    # ----------------------------------------------------------------
    def insert_document(
        self, namespace: str, filename: str, file_type: str,
        blob_path: str = None, metadata: dict = None,
    ) -> str:
        """Registra um documento e retorna o ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (namespace, filename, file_type, blob_path, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (namespace, filename, file_type, blob_path, json.dumps(metadata or {})),
            )
            doc_id = cur.fetchone()[0]
        return str(doc_id)

    def update_document_status(self, doc_id: str, status: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET status = %s WHERE id = %s",
                (status, doc_id),
            )

    # ----------------------------------------------------------------
    # Chunks pai
    # ----------------------------------------------------------------
    def insert_parent_chunk(
        self, doc_id: str, namespace: str, chunk_index: int,
        content: str, metadata: dict = None,
    ) -> str:
        """Insere um chunk pai e retorna o ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO doc_chunks (document_id, namespace, chunk_index, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (doc_id, namespace, chunk_index, content, json.dumps(metadata or {})),
            )
            return str(cur.fetchone()[0])

    # ----------------------------------------------------------------
    # Chunks filho + embedding
    # ----------------------------------------------------------------
    def insert_child_embeddings(
        self, parent_chunk_id: str, doc_id: str, namespace: str,
        children: list[dict],
    ):
        """
        Insere múltiplos chunks filho com seus embeddings.
        children: [{"content": str, "embedding": list[float], "metadata": dict}, ...]
        """
        with self.conn.cursor() as cur:
            for child in children:
                cur.execute(
                    """
                    INSERT INTO doc_chunk_embeddings
                        (parent_chunk_id, document_id, namespace, content, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s::vector, %s)
                    """,
                    (
                        parent_chunk_id,
                        doc_id,
                        namespace,
                        child["content"],
                        str(child["embedding"]),
                        json.dumps(child.get("metadata", {})),
                    ),
                )

    # ----------------------------------------------------------------
    # Fontes estruturadas (Excel/CSV)
    # ----------------------------------------------------------------
    def insert_structured_source(
        self, doc_id: str, namespace: str, sheet_name: str,
        column_schema: dict, sample_rows: list, row_count: int,
        parquet_path: str, description: str = None, metadata: dict = None,
    ):
        """Salva metadados de uma fonte estruturada."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO structured_sources
                    (document_id, namespace, sheet_name, column_schema,
                     sample_rows, row_count, parquet_path, description, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id, namespace, sheet_name,
                    json.dumps(column_schema),
                    json.dumps(sample_rows, default=str),
                    row_count,
                    parquet_path,
                    description,
                    json.dumps(metadata or {}),
                ),
            )

    # ----------------------------------------------------------------
    # Busca vetorial (usado depois, no fluxo de retrieval)
    # ----------------------------------------------------------------
    def search_similar(
        self, namespace: str, query_embedding: list[float], limit: int = 10,
    ) -> list[dict]:
        """Busca os chunks mais similares usando pgvector."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM search_similar(%s, %s::vector, %s)
                """,
                (namespace, str(query_embedding), limit),
            )
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]
        return results

    def get_structured_sources(self, namespace: str) -> list[dict]:
        """Retorna todas as fontes estruturadas de um namespace."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, sheet_name, column_schema, sample_rows,
                       row_count, parquet_path, description
                FROM structured_sources
                WHERE namespace = %s
                """,
                (namespace,),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
