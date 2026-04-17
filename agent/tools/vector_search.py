from storage.pgvector_store import PgVectorStore
from core.gemini import GeminiClient
from config import config

def vector_search_tool(query: str, namespace: str) -> list:
    """Ferramenta de busca vetorial para queries específicas."""
    client = GeminiClient()
    store = PgVectorStore()
    
    embedding = client.embed_texts([query])[0]
    results = store.search_similar(
        namespace=namespace,
        query_embedding=embedding,
        limit=config.app.rag_top_k
    )
    
    store.close()
    return results
