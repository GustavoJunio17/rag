from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import PLANNER_PROMPT
from storage.pgvector_store import PgVectorStore

def planner_node(state: AgentState):
    """Analisa a intenção do usuário e cria um plano de execução."""
    client = GeminiClient()
    store = PgVectorStore()

    # Busca fontes estruturadas disponíveis no namespace
    try:
        structured_sources = store.get_structured_sources(state["namespace"])
    except Exception:
        structured_sources = []
    finally:
        store.close()

    # Monta bloco de contexto sobre arquivos Excel/CSV disponíveis
    if structured_sources:
        sources_info = "\n".join([
            f"- Arquivo: {s.get('parquet_path', '').split('/')[-1]} | Aba: {s.get('sheet_name')} | "
            f"Colunas: {', '.join((s.get('column_schema') or {}).keys())} | Linhas: {s.get('row_count')}"
            for s in structured_sources
        ])
        structured_block = f"\nFontes de dados estruturados disponíveis (Excel/CSV):\n{sources_info}\n"
    else:
        structured_block = "\nNenhuma fonte de dados estruturada disponível.\n"

    history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
    prompt = f"Histórico:\n{history}\n{structured_block}\nPergunta Atual: {state['query']}"

    plan = client.generate_json(prompt, system_instruction=PLANNER_PROMPT)
    plan = plan or {}

    print(f"[Planner] Plan: {plan}")  # debug

    return {
        "sub_tasks": plan.get("tasks", []) if isinstance(plan, dict) else [],
        "current_node": "planner",
        "iteration_count": 0
    }
