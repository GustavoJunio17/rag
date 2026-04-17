from typing import Generator
from storage.pgvector_store import PgVectorStore
from ingestion.pipeline import IngestionPipeline

def get_db() -> Generator:
    db = PgVectorStore()
    try:
        yield db
    finally:
        db.close()

def get_pipeline() -> Generator:
    pipeline = IngestionPipeline()
    try:
        yield pipeline
    finally:
        pipeline.close()

def get_agent():
    from agent.graph import agent
    return agent
