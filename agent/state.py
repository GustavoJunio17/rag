from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    """Estado compartilhado entre os nós do LangGraph."""
    # Obrigatórios na entrada
    messages: List[Dict[str, str]]
    namespace: str
    query: str
    iteration_count: int
    # Preenchidos pelos nós
    sub_tasks: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    graded_chunks: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    context: str
    response_draft: str
    sources: List[Dict[str, Any]]
    final_response: str
    current_node: str
    is_complete: bool
