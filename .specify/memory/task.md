# Task — Plano de Implementação

## Fase 1: Fundação (API + Estrutura)

### Task 1.1 — Reestruturar projeto
- [ ] Reorganizar pastas conforme o plan.md
- [ ] Mover código de ingestão existente para `ingestion/`
- [ ] Criar `main.py` com FastAPI app
- [ ] Atualizar `config.py` com todas as configs (LLM, DB, App, RAG)
- [ ] Atualizar `requirements.txt` com novas dependências
- [ ] Atualizar `.env` com variáveis do Gemini e do app

### Task 1.2 — Camada de API (FastAPI)
- [ ] Criar `api/deps.py` com dependências (get_db, get_pipeline, get_agent)
- [ ] Criar `api/ingestion/schemas.py` (UploadResponse, DocumentResponse, etc.)
- [ ] Criar `api/ingestion/router.py` (upload, list, get, delete)
- [ ] Criar `api/chat/schemas.py` (ChatRequest, ChatResponse, Source, etc.)
- [ ] Criar `api/chat/router.py` (message, stream, history)
- [ ] Registrar routers no `main.py`

### Task 1.3 — Schema do banco (chat)
- [ ] Adicionar tabela `chat_messages` ao schema.sql
- [ ] Adicionar tabela `conversations` ao schema.sql
- [ ] Criar índices por namespace e conversation_id

---

## Fase 2: Core do Agente (LangGraph)

### Task 2.1 — Gemini client centralizado
- [ ] Criar `core/gemini.py` com classe GeminiClient
  - Método `generate(prompt, system_instruction)` → texto
  - Método `generate_json(prompt, system_instruction)` → dict (JSON mode)
  - Método `embed(texts)` → list[list[float]]
  - Configurar modelo via env (GEMINI_MODEL)

### Task 2.2 — Prompts do sistema
- [ ] Criar `core/prompts.py` com todos os prompts:
  - `PLANNER_PROMPT` — analisa intenção e quebra em sub-tarefas
  - `CONTEXT_GRADER_PROMPT` — avalia relevância (score 0-10)
  - `REASONING_PROMPT` — sintetiza resposta com chain-of-thought
  - `QUERY_REFINER_PROMPT` — reformula query
  - `RESPONSE_BUILDER_PROMPT` — formata resposta final com citações
  - `SQL_GENERATOR_PROMPT` — gera SQL a partir de pergunta + schema

### Task 2.3 — Agent State
- [ ] Criar `agent/state.py` com TypedDict do LangGraph:
  ```python
  class AgentState(TypedDict):
      messages: list                    # histórico de conversa
      namespace: str                   # tenant
      query: str                       # pergunta atual
      sub_tasks: list[dict]            # plano do nó 1
      retrieved_chunks: list[dict]     # chunks do RAG
      graded_chunks: list[dict]        # chunks após grading
      tool_results: list[dict]         # resultados das tools
      context: str                     # contexto consolidado
      response_draft: str              # rascunho da resposta
      sources: list[dict]              # fontes citadas
      final_response: str              # resposta final
      iteration_count: int             # controle de loops
      is_complete: bool                # flag de completude
  ```

### Task 2.4 — Nó 1: Planner
- [ ] Criar `agent/nodes/planner.py`
- [ ] Gemini recebe a mensagem + histórico
- [ ] Retorna JSON com lista de sub-tarefas e tipos
- [ ] Tipos: "knowledge_query", "data_query", "comparison", "summary"

### Task 2.5 — Nó 2: RAG Search
- [ ] Criar `agent/nodes/rag_search.py`
- [ ] Gera embedding da query com Gemini
- [ ] Busca no pgvector via `storage.search_similar()`
- [ ] Filtro por namespace
- [ ] Retorna top-K chunks pai com similaridade

### Task 2.6 — Nó 3: Context Grader
- [ ] Criar `agent/nodes/context_grader.py`
- [ ] Gemini avalia cada chunk contra a query (score 0-10)
- [ ] Filtra chunks com score >= threshold (7)
- [ ] Se nenhum chunk passa → marca contexto como fraco

### Task 2.7 — Nó 4: Tool Executor
- [ ] Criar `agent/nodes/tool_executor.py`
- [ ] Criar `agent/tools/vector_search.py` — nova busca vetorial
- [ ] Criar `agent/tools/sql_query.py` — DuckDB em Parquet
  - Recebe pergunta + schema da structured_source
  - Gemini gera SQL
  - DuckDB executa no Parquet
  - Retorna resultado como texto/tabela
- [ ] Criar `agent/tools/web_search.py` — busca web (placeholder)
- [ ] Gemini decide qual tool usar baseado no contexto

### Task 2.8 — Nó 5: Reasoning & Synthesis
- [ ] Criar `agent/nodes/reasoning.py`
- [ ] Consolida todo o contexto (chunks + tools)
- [ ] Gemini faz chain-of-thought
- [ ] Detecta lacunas → se houver, marca para refinamento
- [ ] Se completo, gera resposta rascunho

### Task 2.9 — Nó 6: Query Refiner
- [ ] Criar `agent/nodes/query_refiner.py`
- [ ] Gemini reformula a query com base nas lacunas
- [ ] Incrementa iteration_count
- [ ] Se iteration_count >= MAX (2), força conclusão

### Task 2.10 — Nó 7: Response Builder
- [ ] Criar `agent/nodes/response_builder.py`
- [ ] Formata resposta final com citações
- [ ] Mapeia chunks usados → documentos originais
- [ ] Estrutura sources com filename, page, similarity
- [ ] Se tem dados tabulares, formata como tabela

### Task 2.11 — Montar o Grafo
- [ ] Criar `agent/graph.py`
- [ ] Definir nodes e edges:
  - START → planner
  - planner → rag_search
  - rag_search → context_grader
  - context_grader → tool_executor (se contexto fraco)
  - context_grader → reasoning (se contexto OK)
  - tool_executor → reasoning
  - reasoning → query_refiner (se lacuna)
  - reasoning → response_builder (se completo)
  - query_refiner → rag_search (loop)
  - response_builder → END
- [ ] Compilar grafo com `graph.compile()`

---

## Fase 3: Integração e Polish

### Task 3.1 — Integrar agente com API
- [ ] `api/chat/router.py` instancia e executa o grafo
- [ ] Salva mensagens (user + assistant) no banco
- [ ] Retorna ChatResponse com sources e metadata

### Task 3.2 — Streaming (SSE)
- [ ] Implementar endpoint `/chat/message/stream`
- [ ] Usar `StreamingResponse` do FastAPI
- [ ] LangGraph emite eventos por nó → API converte em SSE

### Task 3.3 — Histórico de conversa
- [ ] Salvar mensagens em `chat_messages`
- [ ] Endpoint GET `/chat/history` retorna histórico
- [ ] Últimas N mensagens passadas como contexto pro agente

### Task 3.4 — Tratamento de erros
- [ ] Timeout de 60s por requisição
- [ ] Retry em caso de rate limit do Gemini
- [ ] Fallback se pgvector estiver fora
- [ ] Logs estruturados em cada nó

### Task 3.5 — Testes
- [ ] Teste unitário de cada nó do LangGraph isolado
- [ ] Teste de integração do grafo completo
- [ ] Teste dos endpoints da API
- [ ] Teste com documento real (DRE 2025 Senior.PDF)

---

## Ordem de Execução Recomendada

```
1.1 → 1.3 → 2.1 → 2.2 → 2.3 → 2.5 → 2.6 → 2.4 → 2.7 → 2.8 → 2.9 → 2.10
→ 2.11 → 1.2 → 3.1 → 3.3 → 3.2 → 3.4 → 3.5
```

Comece pelo banco e core (Gemini + State), depois os nós do LangGraph um a um,
depois a API, e por último streaming e polish.
