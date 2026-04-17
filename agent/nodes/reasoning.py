from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import REASONING_PROMPT

def reasoning_node(state: AgentState):
    """Sintetiza as informações e gera a resposta."""
    client = GeminiClient()
    
    # Consolida contexto
    context_parts = []
    for chunk in state.get("graded_chunks", []):
        context_parts.append(f"Documento: {chunk['metadata'].get('filename')}\n{chunk['parent_content']}")
        
    for res in state.get("tool_results", []):
        context_parts.append(f"Resultado de Ferramenta:\n{res['result']}")
        
    context = "\n\n---\n\n".join(context_parts)
    
    prompt = f"Pergunta: {state['query']}\n\nContexto:\n{context}"
    response = client.generate(prompt, system_instruction=REASONING_PROMPT)
    
    # Detecta se a resposta parece incompleta
    incomplete_signals = [
        "não encontrei", "não foi possível encontrar", "não há informações",
        "não tenho informações", "não consta", "sem informação", "não disponível",
        "informação insuficiente", "não foi encontrado"
    ]
    is_complete = not any(signal in response.lower() for signal in incomplete_signals)
    
    return {
        "context": context,
        "response_draft": response,
        "is_complete": is_complete,
        "current_node": "reasoning"
    }
