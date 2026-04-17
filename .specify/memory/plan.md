# Plan — Arquitetura e Decisões Técnicas

## 1. Estrutura de Pastas

```
rag/
├── main.py                          # Entry point FastAPI
├── config.py                        # Configurações centrais
├── requirements.txt
├── docker-compose.yml
├── .env
│
├── db/
│   └── schema.sql                   # Schema completo (ingestão + chat)
│
├── api/
│   ├── __init__.py
│   ├── deps.py                      # Dependências compartilhadas (get_db, get_embedder, etc.)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── router.py                # Endpoints de ingestão
│   │   └── schemas.py               # Pydantic models (request/response)
│   └── chat/
│       ├── __init__.py
│       ├── router.py                # Endpoints de chat
│       └── schemas.py               # Pydantic models (request/response)
│
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py                  # Orquestrador (antigo ingestion.py)
│   ├── loaders/
│   │   ├── __init__.py              # BaseLoader + detect_loader
│   │   ├── pdf_loader.py
│   │   ├── docx_loader.py
│   │   ├── excel_loader.py
│   │   └── txt_loader.py
│   ├── chunking/
│   │   └── __init__.py              # HierarchicalChunker
│   └── embeddings/
│       └── __init__.py              # Embedder (Gemini)
│
├── agent/
│   ├── __init__.py
│   ├── graph.py                     # Definição do grafo LangGraph (7 nós)
│   ├── state.py                     # AgentState (TypedDict do LangGraph)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planner.py               # Nó 1 — Planner / Task Decomposer
│   │   ├── rag_search.py            # Nó 2 — Multi-vector RAG Search
│   │   ├── context_grader.py        # Nó 3 — Context Grader & Filter
│   │   ├── tool_executor.py         # Nó 4 — Tool Executor
│   │   ├── reasoning.py             # Nó 5 — Reasoning & Synthesis
│   │   ├── query_refiner.py         # Nó 6 — Query Refiner
│   │   └── response_builder.py     # Nó 7 — Multi-modal Response
│   └── tools/
│       ├── __init__.py
│       ├── vector_search.py         # Tool: busca vetorial no pgvector
│       ├── sql_query.py             # Tool: query DuckDB em Parquet
│       └── web_search.py            # Tool: busca na web (opcional)
│
├── storage/
│   ├── __init__.py
│   └── pgvector_store.py            # Interface com pgvector (já existe)
│
└── core/
    ├── __init__.py
    ├── gemini.py                    # Client Gemini centralizado
    └── prompts.py                   # Todos os prompts do sistema
```

---

## 2. Decisões de Arquitetura

### 2.1 — FastAPI como camada fina
A API é apenas uma camada de roteamento. A lógica de negócio fica em `ingestion/` (pipeline) e `agent/` (LangGraph). Isso permite testar o agente sem a API e vice-versa.

### 2.2 — LangGraph como orquestrador
O grafo do LangGraph mapeia 1:1 com o diagrama do usuário:
- Cada nó é um arquivo em `agent/nodes/`
- O estado compartilhado (`AgentState`) flui entre os nós
- Edges condicionais controlam os loops de refinamento

### 2.3 — Gemini centralizado
Um único client Gemini em `core/gemini.py` é usado por todos os nós. Isso evita instanciar múltiplos clients e facilita trocar o modelo.

### 2.4 — Prompts separados
Todos os prompts do sistema ficam em `core/prompts.py`. Cada nó do LangGraph usa um prompt específico. Isso facilita iterar nos prompts sem mexer na lógica.

### 2.5 — DuckDB para dados tabulares
Em vez de carregar Excel em pandas a cada query, o DuckDB lê Parquet nativamente com SQL. Mais rápido, menos memória, e o LLM gera SQL melhor que código pandas.

### 2.6 — Storage layer compartilhado
O `storage/pgvector_store.py` é usado tanto pela ingestão quanto pelo agente. Centraliza todas as operações de banco.

---

## 3. Fluxo de Dados

### Upload + Ingestão
```
[Cliente] → POST /api/v1/ingestion/upload
    → [FastAPI] salva arquivo em disco/blob
    → [BackgroundTask] chama ingestion.pipeline.ingest()
    → [Pipeline] extrai → chunkeia → embedding → salva pgvector
    → [DB] documents, doc_chunks, doc_chunk_embeddings, structured_sources
```

### Chat
```
[Cliente] → POST /api/v1/chat/message { message, namespace }
    → [FastAPI] cria/recupera conversation
    → [LangGraph] executa o grafo:
        → Nó 1: Planner analisa intenção
        → Nó 2: RAG busca no pgvector
        → Nó 3: Grader avalia relevância
        → Nó 4: Tools (se necessário)
        → Nó 5: Reasoning sintetiza
        → Nó 6: Refiner (se lacuna) → volta ao nó 2
        → Nó 7: Response formata com citações
    → [FastAPI] salva mensagens no histórico
    → [Cliente] recebe resposta + fontes
```

---

## 4. Dependências Principais

| Pacote | Versão | Uso |
|--------|--------|-----|
| fastapi | >=0.115.0 | API REST |
| uvicorn | >=0.30.0 | Server ASGI |
| langgraph | >=0.2.0 | Orquestração do agente |
| langchain-core | >=0.3.0 | Base para tools e messages |
| google-genai | >=1.0.0 | Gemini LLM + embeddings |
| psycopg[binary] | >=3.2.0 | PostgreSQL driver |
| pgvector | >=0.3.0 | Extensão vetorial |
| duckdb | >=1.1.0 | SQL em Parquet |
| pydantic | >=2.9.0 | Validação de dados |
| python-multipart | >=0.0.9 | Upload de arquivos |

---

## 5. Configuração de Ambiente

```env
# LLM
GEMINI_API_KEY=sua-chave
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Banco
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=gestores_ia
PG_USER=postgres
PG_PASSWORD=postgres

# App
APP_HOST=0.0.0.0
APP_PORT=8000
RAG_TOP_K=8
RAG_RELEVANCE_THRESHOLD=7
MAX_REFINEMENT_ITERATIONS=2
CONVERSATION_HISTORY_LIMIT=10
```
