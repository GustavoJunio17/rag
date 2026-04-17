from agent.state import AgentState
from agent.tools.sql_query import sql_query_tool
from agent.tools.vector_search import vector_search_tool

def tool_executor_node(state: AgentState):
    """Executa as ferramentas necessárias para completar o contexto."""
    # Nó 4 só é chamado se o context_grader falhar ou se o planner pedir explicitamente.
    # Para o MVP do Nó 4, focamos em executar sub-tarefas do Planner.
    
    results = []
    for task in state.get("sub_tasks", []):
        task_type = task.get("type")
        task_query = task.get("query")
        task_id = task.get("id")
        
        if task_type == "data_query":
            res = sql_query_tool(task_query, state["namespace"])
            results.append({"task_id": task_id, "result": res})
        elif task_type == "vector_search":
            res = vector_search_tool(task_query, state["namespace"])
            results.append({"task_id": task_id, "result": res})
            
    return {
        "tool_results": results,
        "current_node": "tool_executor"
    }
