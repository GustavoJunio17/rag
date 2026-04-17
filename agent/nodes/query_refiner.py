from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import QUERY_REFINER_PROMPT
from config import config

def query_refiner_node(state: AgentState):
    """Reformula a query para buscar o que falta."""
    client = GeminiClient()
    
    prompt = f"Pergunta original: {state['query']}\nO que já temos: {state['response_draft']}"
    new_query = client.generate(prompt, system_instruction=QUERY_REFINER_PROMPT)
    
    # Incrementa contador de iterações
    iteration_count = state.get("iteration_count", 0) + 1
    
    return {
        "query": new_query.strip(),
        "iteration_count": iteration_count,
        "current_node": "query_refiner"
    }
