from typing import Literal
from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes.planner import planner_node
from agent.nodes.rag_search import rag_search_node
from agent.nodes.context_grader import context_grader_node
from agent.nodes.tool_executor import tool_executor_node
from agent.nodes.reasoning import reasoning_node
from agent.nodes.query_refiner import query_refiner_node
from agent.nodes.response_builder import response_builder_node
from config import config

# --- Auxiliares de Roteamento ---

def decide_after_planner(state: AgentState) -> Literal["tool_executor", "rag_search"]:
    """Se o planner identificou data_query, vai direto para SQL. Senão, faz RAG."""
    has_data_query = any(
        t.get("type") == "data_query" for t in state.get("sub_tasks", [])
    )
    if has_data_query:
        return "tool_executor"
    return "rag_search"

def decide_after_grader(state: AgentState) -> Literal["tool_executor", "reasoning"]:
    """Decide se busca mais ferramentas ou vai para a síntese."""
    if not state.get("graded_chunks", []):
        return "tool_executor"
    return "reasoning"

def decide_after_reasoning(state: AgentState) -> Literal["query_refiner", "response_builder"]:
    """Decide se a resposta está completa ou se precisa de mais informações."""
    if not state["is_complete"] and state.get("iteration_count", 0) < config.app.max_refinement_iterations:
        return "query_refiner"
    return "response_builder"

# --- Construção do Grafo ---

def create_agent_graph():
    """Cria e compila o grafo do LangGraph."""
    workflow = StateGraph(AgentState)

    # Adiciona os Nós
    workflow.add_node("planner", planner_node)
    workflow.add_node("rag_search", rag_search_node)
    workflow.add_node("context_grader", context_grader_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("query_refiner", query_refiner_node)
    workflow.add_node("response_builder", response_builder_node)

    # Edges fixas
    workflow.add_edge(START, "planner")
    workflow.add_edge("rag_search", "context_grader")
    workflow.add_edge("tool_executor", "reasoning")
    workflow.add_edge("query_refiner", "rag_search")  # loop de refinamento
    workflow.add_edge("response_builder", END)

    # Roteamento após planner: data_query → SQL direto, senão → RAG
    workflow.add_conditional_edges(
        "planner",
        decide_after_planner,
        {
            "tool_executor": "tool_executor",
            "rag_search": "rag_search",
        }
    )

    # Roteamento após grader: sem chunks relevantes → SQL, senão → reasoning
    workflow.add_conditional_edges(
        "context_grader",
        decide_after_grader,
        {
            "tool_executor": "tool_executor",
            "reasoning": "reasoning",
        }
    )

    # Roteamento após reasoning: incompleto → refina, completo → formata resposta
    workflow.add_conditional_edges(
        "reasoning",
        decide_after_reasoning,
        {
            "query_refiner": "query_refiner",
            "response_builder": "response_builder",
        }
    )

    return workflow.compile()

# Instância compilada do agente
agent = create_agent_graph()
