from agent.state import AgentState
from core.gemini import GeminiClient
from storage.pgvector_store import PgVectorStore
from config import config

def rag_search_node(state: AgentState):
    """Busca chunks relevantes no banco vetorial."""
    client = GeminiClient()
    store = PgVectorStore()
    
    # Gera embedding para a query atual
    # Para o Nó 2, usamos a query principal. Nos loops de refinamento, a query muda.
    query_text = state["query"]
    embedding = client.embed_texts([query_text])[0]
    
    # Busca no pgvector
    results = store.search_similar(
        namespace=state["namespace"],
        query_embedding=embedding,
        limit=config.app.rag_top_k
    )
    
    store.close()
    
    return {
        "retrieved_chunks": results,
        "current_node": "rag_search"
    }
