# Implement — Guia de Implementação

Este documento detalha COMO implementar cada componente, com padrões de código,
assinaturas e exemplos concretos.

---

## 1. Entry Point — `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ingestion.router import router as ingestion_router
from api.chat.router import router as chat_router

app = FastAPI(
    title="IA para Gestores",
    version="1.0.0",
    description="API de RAG com LangGraph para documentos empresariais",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router, prefix="/api/v1/ingestion", tags=["Ingestão"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## 2. Gemini Client — `core/gemini.py`

Padrão singleton. Todos os nós do LangGraph usam este client.

```python
from google import genai
from config import config

class GeminiClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = genai.Client(api_key=config.gemini_api_key)
            cls._instance.model = config.gemini_model
            cls._instance.embedding_model = config.gemini_embedding_model
        return cls._instance

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        """Gera texto com Gemini."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,  # Baixa para respostas factuais
            ),
        )
        return response.text

    def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        """Gera JSON estruturado com Gemini."""
        import json
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        return json.loads(response.text)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings com Gemini."""
        result = self.client.models.embed_content(
            model=self.embedding_model,
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def embed_query(self, text: str) -> list[float]:
        """Embedding de uma única query."""
        return self.embed([text])[0]
```

---

## 3. Agent State — `agent/state.py`

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Entrada
    messages: Annotated[list, add_messages]  # histórico com redução automática
    namespace: str
    query: str

    # Nó 1 — Planner
    sub_tasks: list[dict]           # [{"task": "...", "type": "knowledge_query"}]

    # Nó 2 — RAG Search
    retrieved_chunks: list[dict]    # [{"content": "...", "similarity": 0.89, ...}]

    # Nó 3 — Context Grader
    graded_chunks: list[dict]       # chunks que passaram no threshold
    context_quality: str            # "strong" | "weak"

    # Nó 4 — Tool Executor
    tool_results: list[dict]        # [{"tool": "sql_query", "result": "..."}]

    # Nó 5 — Reasoning
    consolidated_context: str       # contexto final montado
    has_gaps: bool                  # True se faltou informação
    gap_description: str            # o que está faltando

    # Nó 6 — Query Refiner
    refined_query: str
    iteration_count: int            # max 2

    # Nó 7 — Response
    final_response: str
    sources: list[dict]
```

---

## 4. Nós do LangGraph — Padrão

Cada nó é uma função que recebe `AgentState` e retorna um dict parcial:

```python
# Padrão de um nó:
def node_name(state: AgentState) -> dict:
    # 1. Lê o que precisa do state
    # 2. Processa (chama Gemini, busca no banco, etc.)
    # 3. Retorna APENAS os campos que modifica
    return {"campo_modificado": novo_valor}
```

### 4.1 — Planner (`agent/nodes/planner.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import PLANNER_PROMPT

def planner(state: AgentState) -> dict:
    gemini = GeminiClient()

    prompt = f"""
    Pergunta do usuário: {state["query"]}

    Histórico recente:
    {format_history(state.get("messages", []))}
    """

    result = gemini.generate_json(prompt, system_instruction=PLANNER_PROMPT)

    return {
        "sub_tasks": result.get("tasks", [{"task": state["query"], "type": "knowledge_query"}]),
    }
```

### 4.2 — RAG Search (`agent/nodes/rag_search.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from storage import PgVectorStore
from config import config

def rag_search(state: AgentState) -> dict:
    gemini = GeminiClient()
    store = PgVectorStore()

    # Usa query refinada se existir, senão a original
    query = state.get("refined_query") or state["query"]

    # Gera embedding da query
    query_embedding = gemini.embed_query(query)

    # Busca no pgvector
    results = store.search_similar(
        namespace=state["namespace"],
        query_embedding=query_embedding,
        limit=config.rag_top_k,  # default 8
    )

    return {"retrieved_chunks": results}
```

### 4.3 — Context Grader (`agent/nodes/context_grader.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import CONTEXT_GRADER_PROMPT
from config import config

def context_grader(state: AgentState) -> dict:
    gemini = GeminiClient()
    chunks = state["retrieved_chunks"]

    if not chunks:
        return {"graded_chunks": [], "context_quality": "weak"}

    # Avalia relevância de cada chunk em batch
    chunks_text = "\n---\n".join(
        f"Chunk {i+1}: {c['parent_content'][:500]}"
        for i, c in enumerate(chunks)
    )

    prompt = f"""
    Query: {state["query"]}

    Chunks recuperados:
    {chunks_text}
    """

    result = gemini.generate_json(prompt, system_instruction=CONTEXT_GRADER_PROMPT)
    # Esperado: {"scores": [{"index": 0, "score": 8}, ...]}

    threshold = config.rag_relevance_threshold  # default 7
    graded = []
    for score_item in result.get("scores", []):
        idx = score_item["index"]
        if score_item["score"] >= threshold and idx < len(chunks):
            chunks[idx]["relevance_score"] = score_item["score"]
            graded.append(chunks[idx])

    quality = "strong" if graded else "weak"
    return {"graded_chunks": graded, "context_quality": quality}
```

### 4.4 — Tool Executor (`agent/nodes/tool_executor.py`)

```python
from agent.state import AgentState
from agent.tools.vector_search import vector_search_tool
from agent.tools.sql_query import sql_query_tool
from core.gemini import GeminiClient

def tool_executor(state: AgentState) -> dict:
    gemini = GeminiClient()

    # Gemini decide qual tool usar
    decision = gemini.generate_json(
        f"Query: {state['query']}\nContexto fraco. Qual ferramenta usar?",
        system_instruction="Retorne JSON: {\"tool\": \"vector_search\" | \"sql_query\", \"params\": {...}}"
    )

    tool_name = decision.get("tool", "vector_search")
    results = []

    if tool_name == "vector_search":
        result = vector_search_tool(state["namespace"], decision.get("params", {}).get("query", state["query"]))
        results.append({"tool": "vector_search", "result": result})
    elif tool_name == "sql_query":
        result = sql_query_tool(state["namespace"], state["query"])
        results.append({"tool": "sql_query", "result": result})

    return {"tool_results": results}
```

### 4.5 — SQL Query Tool (`agent/tools/sql_query.py`)

```python
import duckdb
import json
from storage import PgVectorStore
from core.gemini import GeminiClient

def sql_query_tool(namespace: str, question: str) -> str:
    """Executa SQL em fontes estruturadas (Excel/CSV em Parquet)."""
    store = PgVectorStore()
    gemini = GeminiClient()

    # 1. Busca schemas das fontes estruturadas do namespace
    sources = store.get_structured_sources(namespace)
    if not sources:
        return "Nenhuma fonte estruturada encontrada neste namespace."

    # 2. Monta contexto com schemas pra o Gemini gerar SQL
    schemas_text = "\n".join(
        f"Tabela '{s['sheet_name']}' (arquivo: {s['parquet_path']}):\n"
        f"  Colunas: {json.dumps(s['column_schema'])}\n"
        f"  Linhas: {s['row_count']}\n"
        f"  Amostra: {json.dumps(s['sample_rows'][:3], default=str)}"
        for s in sources
    )

    # 3. Gemini gera o SQL
    sql_result = gemini.generate_json(
        f"Pergunta: {question}\n\nSchemas disponíveis:\n{schemas_text}",
        system_instruction=(
            "Gere uma query SQL DuckDB para responder a pergunta. "
            "Use read_parquet('caminho') para acessar os dados. "
            "Retorne JSON: {\"sql\": \"SELECT ...\", \"explanation\": \"...\"}"
        ),
    )

    sql = sql_result.get("sql", "")
    if not sql:
        return "Não foi possível gerar SQL para esta pergunta."

    # 4. Executa no DuckDB
    try:
        conn = duckdb.connect()
        result = conn.execute(sql).fetchdf()
        conn.close()
        return f"Query: {sql}\n\nResultado:\n{result.to_string(index=False)}"
    except Exception as e:
        return f"Erro ao executar SQL: {e}\nSQL tentado: {sql}"
```

### 4.6 — Reasoning (`agent/nodes/reasoning.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import REASONING_PROMPT

def reasoning(state: AgentState) -> dict:
    gemini = GeminiClient()

    # Consolida contexto
    context_parts = []

    for chunk in state.get("graded_chunks", []):
        context_parts.append(f"[Doc: {chunk.get('metadata', {}).get('filename', '?')}]\n{chunk['parent_content']}")

    for tool_result in state.get("tool_results", []):
        context_parts.append(f"[Ferramenta: {tool_result['tool']}]\n{tool_result['result']}")

    consolidated = "\n\n---\n\n".join(context_parts)

    prompt = f"""
    Pergunta: {state["query"]}

    Contexto disponível:
    {consolidated}
    """

    result = gemini.generate_json(prompt, system_instruction=REASONING_PROMPT)

    return {
        "consolidated_context": consolidated,
        "has_gaps": result.get("has_gaps", False),
        "gap_description": result.get("gap_description", ""),
        "final_response": result.get("response", ""),
    }
```

### 4.7 — Query Refiner (`agent/nodes/query_refiner.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import QUERY_REFINER_PROMPT

def query_refiner(state: AgentState) -> dict:
    gemini = GeminiClient()
    iteration = state.get("iteration_count", 0) + 1

    prompt = f"""
    Query original: {state["query"]}
    Lacuna detectada: {state.get("gap_description", "")}
    Iteração: {iteration}
    """

    result = gemini.generate_json(prompt, system_instruction=QUERY_REFINER_PROMPT)

    return {
        "refined_query": result.get("refined_query", state["query"]),
        "iteration_count": iteration,
    }
```

### 4.8 — Response Builder (`agent/nodes/response_builder.py`)

```python
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import RESPONSE_BUILDER_PROMPT

def response_builder(state: AgentState) -> dict:
    gemini = GeminiClient()

    # Mapeia sources
    sources = []
    for chunk in state.get("graded_chunks", []):
        meta = chunk.get("metadata", {})
        sources.append({
            "document": meta.get("filename", "desconhecido"),
            "chunk": chunk.get("parent_content", "")[:200],
            "page": meta.get("page", None),
            "similarity": chunk.get("similarity", 0),
        })

    for tool_result in state.get("tool_results", []):
        sources.append({
            "document": f"Ferramenta: {tool_result['tool']}",
            "chunk": str(tool_result["result"])[:200],
        })

    prompt = f"""
    Resposta bruta: {state.get("final_response", "")}
    Fontes disponíveis: {len(sources)} documentos
    """

    final = gemini.generate(prompt, system_instruction=RESPONSE_BUILDER_PROMPT)

    return {
        "final_response": final,
        "sources": sources,
    }
```

---

## 5. Montagem do Grafo — `agent/graph.py`

```python
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.planner import planner
from agent.nodes.rag_search import rag_search
from agent.nodes.context_grader import context_grader
from agent.nodes.tool_executor import tool_executor
from agent.nodes.reasoning import reasoning
from agent.nodes.query_refiner import query_refiner
from agent.nodes.response_builder import response_builder
from config import config


def should_use_tools(state: AgentState) -> str:
    """Edge condicional após context_grader."""
    if state.get("context_quality") == "weak":
        return "tool_executor"
    return "reasoning"


def should_refine(state: AgentState) -> str:
    """Edge condicional após reasoning."""
    if state.get("has_gaps") and state.get("iteration_count", 0) < config.max_refinement_iterations:
        return "query_refiner"
    return "response_builder"


def build_graph():
    graph = StateGraph(AgentState)

    # Adiciona nós
    graph.add_node("planner", planner)
    graph.add_node("rag_search", rag_search)
    graph.add_node("context_grader", context_grader)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("reasoning", reasoning)
    graph.add_node("query_refiner", query_refiner)
    graph.add_node("response_builder", response_builder)

    # Edges lineares
    graph.set_entry_point("planner")
    graph.add_edge("planner", "rag_search")
    graph.add_edge("rag_search", "context_grader")
    graph.add_edge("tool_executor", "reasoning")
    graph.add_edge("query_refiner", "rag_search")       # loop de refinamento
    graph.add_edge("response_builder", END)

    # Edges condicionais
    graph.add_conditional_edges("context_grader", should_use_tools)
    graph.add_conditional_edges("reasoning", should_refine)

    return graph.compile()


# Instância global do grafo compilado
agent_graph = build_graph()
```

---

## 6. Chat Router — `api/chat/router.py`

```python
from fastapi import APIRouter, HTTPException
from api.chat.schemas import ChatRequest, ChatResponse
from agent.graph import agent_graph

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        # Executa o grafo
        result = agent_graph.invoke({
            "query": request.message,
            "namespace": request.namespace,
            "messages": [],  # TODO: carregar histórico do banco
            "iteration_count": 0,
        })

        return ChatResponse(
            response=result["final_response"],
            sources=result.get("sources", []),
            conversation_id=request.conversation_id,
            metadata={
                "tools_used": [t["tool"] for t in result.get("tool_results", [])],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7. Prompts — `core/prompts.py`

Padrão: cada prompt é uma string com instruções claras para o Gemini.

```python
PLANNER_PROMPT = """
Você é um planejador de tarefas para uma IA de gestão empresarial.
Analise a pergunta do usuário e quebre em sub-tarefas se necessário.

Retorne JSON:
{
  "tasks": [
    {"task": "descrição da sub-tarefa", "type": "knowledge_query | data_query | comparison | summary"}
  ],
  "reasoning": "por que você decidiu esse plano"
}

Tipos de tarefa:
- knowledge_query: buscar informação em documentos textuais (PDF, DOCX)
- data_query: buscar dados numéricos em planilhas (Excel/CSV)
- comparison: comparar dois ou mais itens
- summary: resumir informações

Se a pergunta for simples e direta, retorne apenas uma tarefa.
"""

CONTEXT_GRADER_PROMPT = """
Você é um avaliador de relevância de contexto.
Dada uma query e chunks de documentos recuperados, avalie a relevância de cada chunk
numa escala de 0 a 10.

0 = completamente irrelevante
5 = parcialmente relevante
10 = exatamente o que a query pede

Retorne JSON:
{
  "scores": [
    {"index": 0, "score": 8, "reason": "contém dados financeiros do período solicitado"}
  ]
}
"""

REASONING_PROMPT = """
Você é um analista que sintetiza informações de documentos empresariais.
Com base no contexto fornecido, responda à pergunta do usuário.

Regras:
1. Use APENAS informações presentes no contexto — nunca invente dados
2. Se o contexto não contiver informação suficiente, defina has_gaps como true
3. Cite os documentos de onde veio cada informação
4. Para dados numéricos, seja preciso

Retorne JSON:
{
  "response": "resposta completa aqui",
  "has_gaps": false,
  "gap_description": "descrição do que falta (se has_gaps=true)",
  "confidence": 0.85
}
"""

QUERY_REFINER_PROMPT = """
A busca anterior não retornou contexto suficiente.
Reformule a query para tentar encontrar a informação que falta.

Estratégias:
- Use sinônimos ou termos alternativos
- Seja mais específico ou mais genérico
- Foque na lacuna descrita

Retorne JSON:
{
  "refined_query": "nova query reformulada",
  "strategy": "o que você mudou e por quê"
}
"""

RESPONSE_BUILDER_PROMPT = """
Formate a resposta final para o gestor.
A resposta deve ser:
- Clara e objetiva
- Com citações dos documentos entre [colchetes]
- Dados numéricos destacados
- Em português brasileiro
- Profissional mas acessível

Não use markdown excessivo. Foque na clareza.
"""

SQL_GENERATOR_PROMPT = """
Você é um gerador de SQL para DuckDB.
Gere queries SQL para responder perguntas sobre dados tabulares.

Use read_parquet('caminho_do_arquivo') para acessar os dados.
Exemplo: SELECT * FROM read_parquet('/path/to/file.parquet') WHERE coluna > 100

Retorne JSON:
{
  "sql": "SELECT ...",
  "explanation": "explicação do que a query faz"
}

IMPORTANTE: Use os nomes exatos das colunas do schema fornecido.
"""
```

---

## 8. Notas de Implementação

### Rate Limiting do Gemini
- Free tier: 15 RPM (requests por minuto)
- Adicione `time.sleep(0.5)` entre chamadas se necessário
- Em produção, use exponential backoff

### Conexões de Banco
- Use connection pool em produção (psycopg_pool)
- Para dev, conexão simples com autocommit funciona

### Testes Rápidos
```bash
# Subir a API
uvicorn main:app --reload --port 8000

# Testar ingestão
curl -X POST http://localhost:8000/api/v1/ingestion/upload \
  -F "file=@DRE 2025 Senior.PDF" \
  -F "namespace=statum"

# Testar chat
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual foi o faturamento total?", "namespace": "statum"}'
```
