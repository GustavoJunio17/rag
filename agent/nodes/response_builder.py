from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import RESPONSE_BUILDER_PROMPT

def response_builder_node(state: AgentState):
    """Formata a resposta final com fontes e metadados."""
    client = GeminiClient()
    
    prompt = f"Rascunho: {state['response_draft']}"
    final_response = client.generate(prompt, system_instruction=RESPONSE_BUILDER_PROMPT)
    
    # Extrai fontes únicas para o metadado
    sources = []
    seen_docs = set()
    for chunk in state.get("graded_chunks", []):
        doc_name = chunk["metadata"].get("filename")
        if doc_name and doc_name not in seen_docs:
            sources.append({
                "document": doc_name,
                "page": chunk["metadata"].get("page"),
                "similarity": chunk.get("similarity", 0)
            })
            seen_docs.add(doc_name)
            
    return {
        "final_response": final_response,
        "sources": sources,
        "is_complete": True,
        "current_node": "response_builder"
    }
