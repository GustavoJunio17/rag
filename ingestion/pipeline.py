"""
Orquestrador principal de ingestão.

Fluxo completo (conforme diagrama):
1. Recebe arquivo + namespace
2. Detecta tipo e extrai conteúdo
3. Se estruturado (Excel/CSV): salva em structured_sources + Parquet
4. Faz chunking hierárquico (pai/filho)
5. Gera embeddings dos chunks filho
6. Salva tudo no pgvector
"""

import argparse
import os
import sys
from pathlib import Path
from tqdm import tqdm

from config import config
from ingestion.loaders import BaseLoader
from ingestion.chunking import HierarchicalChunker
from ingestion.embeddings import Embedder
from storage import PgVectorStore


class IngestionPipeline:
    """Pipeline completo de ingestão de documentos."""

    def __init__(self):
        self.chunker = HierarchicalChunker()
        self.embedder = Embedder()
        self.store = PgVectorStore()

    def ingest(self, file_path: str, namespace: str) -> dict:
        """
        Ingere um arquivo completo.

        Args:
            file_path: Caminho do arquivo (PDF, DOCX, XLSX, CSV, TXT)
            namespace: Identificador do tenant (empresa/gestor)

        Returns:
            Resumo da ingestão com contagens.
        """
        file_path = os.path.abspath(file_path)
        filename = Path(file_path).name

        print(f"\n{'='*60}")
        print(f"Ingerindo: {filename}")
        print(f"Namespace: {namespace}")
        print(f"{'='*60}\n")

        # 1. Registra o documento no banco
        loader = BaseLoader.detect_loader(file_path)
        file_type = file_path.rsplit(".", 1)[-1].lower()

        doc_id = self.store.insert_document(
            namespace=namespace,
            filename=filename,
            file_type=file_type,
            blob_path=file_path,
        )
        print(f"[1/5] Documento registrado: {doc_id}")

        try:
            # 2. Extrai conteúdo
            print(f"[2/5] Extraindo conteúdo com {type(loader).__name__}...")
            content = loader.extract(file_path)
            print(f"       Texto extraído: {len(content.text)} chars")

            stats = {
                "doc_id": doc_id,
                "filename": filename,
                "namespace": namespace,
                "parent_chunks": 0,
                "child_chunks": 0,
                "structured_sources": 0,
            }

            # 3. Se for dado estruturado, salva em structured_sources
            if content.is_structured and content.structured_data:
                print(f"[3/5] Salvando {len(content.structured_data)} fonte(s) estruturada(s)...")
                for sheet_data in content.structured_data:
                    self.store.insert_structured_source(
                        doc_id=doc_id,
                        namespace=namespace,
                        sheet_name=sheet_data["sheet_name"],
                        column_schema=sheet_data["schema"],
                        sample_rows=sheet_data["sample"],
                        row_count=sheet_data["row_count"],
                        parquet_path=sheet_data["parquet_path"],
                    )
                    stats["structured_sources"] += 1
                    print(f"       → {sheet_data['sheet_name']}: {sheet_data['row_count']} linhas")
            else:
                print(f"[3/5] Não é dado estruturado, pulando...")

            # 4. Chunking hierárquico
            print(f"[4/5] Chunking hierárquico...")
            base_metadata = {
                "filename": filename,
                "file_type": file_type,
                **content.metadata,
            }
            parent_chunks = self.chunker.chunk(content.text, base_metadata)
            stats["parent_chunks"] = len(parent_chunks)
            print(f"       {len(parent_chunks)} chunks pai criados")

            # 5. Embeddings + salvamento
            print(f"[5/5] Gerando embeddings e salvando...")

            for parent in tqdm(parent_chunks, desc="Processando chunks"):
                # Salva chunk pai
                parent_db_id = self.store.insert_parent_chunk(
                    doc_id=doc_id,
                    namespace=namespace,
                    chunk_index=parent.chunk_index,
                    content=parent.content,
                    metadata=parent.metadata,
                )

                # Gera embeddings dos filhos em batch
                child_texts = [c.content for c in parent.children]
                child_embeddings = self.embedder.embed_texts(child_texts)

                # Salva filhos com embeddings
                children_data = [
                    {
                        "content": child.content,
                        "embedding": embedding,
                        "metadata": child.metadata,
                    }
                    for child, embedding in zip(parent.children, child_embeddings)
                ]

                self.store.insert_child_embeddings(
                    parent_chunk_id=parent_db_id,
                    doc_id=doc_id,
                    namespace=namespace,
                    children=children_data,
                )
                stats["child_chunks"] += len(children_data)

            # Marca como completo
            self.store.update_document_status(doc_id, "completed")

            print(f"\n{'='*60}")
            print(f"Ingestão completa!")
            print(f"  Chunks pai:           {stats['parent_chunks']}")
            print(f"  Chunks filho:         {stats['child_chunks']}")
            print(f"  Fontes estruturadas:  {stats['structured_sources']}")
            print(f"{'='*60}\n")

            return stats

        except Exception as e:
            self.store.update_document_status(doc_id, "failed")
            print(f"\nERRO na ingestão: {e}")
            raise

    def close(self):
        self.store.close()


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pipeline de ingestão de documentos")
    parser.add_argument("--file", "-f", required=True, help="Caminho do arquivo")
    parser.add_argument("--namespace", "-n", required=True, help="Namespace (tenant)")
    parser.add_argument(
        "--dir", "-d",
        help="Processar todos os arquivos de um diretório",
    )

    args = parser.parse_args()
    pipeline = IngestionPipeline()

    try:
        if args.dir:
            # Modo batch: processa todos os arquivos do diretório
            dir_path = Path(args.dir)
            supported = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".md"}
            files = [f for f in dir_path.iterdir() if f.suffix.lower() in supported]

            print(f"Encontrados {len(files)} arquivos para processar")
            for file in files:
                pipeline.ingest(str(file), args.namespace)
        else:
            pipeline.ingest(args.file, args.namespace)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
