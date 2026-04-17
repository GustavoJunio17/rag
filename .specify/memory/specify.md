# Specify — Requisitos Funcionais

## 1. Visão Geral da API

A API expõe dois domínios principais:

- **Ingestão** (`/api/v1/ingestion/`) — upload e processamento de documentos
- **Chat** (`/api/v1/chat/`) — conversação com a IA sobre os documentos

---

## 2. Endpoints de Ingestão

### POST `/api/v1/ingestion/upload`
- **Input**: arquivo (multipart) + namespace (string)
- **Processo**: salva arquivo localmente (ou Blob), dispara pipeline de ingestão
- **Output**: `{ doc_id, filename, status: "processing" | "completed" | "failed" }`
- **Async**: a ingestão pode rodar em background (BackgroundTasks do FastAPI)

### GET `/api/v1/ingestion/documents`
- **Input**: namespace (query param)
- **Output**: lista de documentos ingeridos com status

### GET `/api/v1/ingestion/documents/{doc_id}`
- **Input**: doc_id (path param)
- **Output**: detalhes do documento (status, metadata, chunks count)

### DELETE `/api/v1/ingestion/documents/{doc_id}`
- **Input**: doc_id (path param)
- **Processo**: remove documento, chunks e embeddings do banco
- **Output**: `{ deleted: true }`

---

## 3. Endpoints de Chat

### POST `/api/v1/chat/message`
- **Input**:
  ```json
  {
    "message": "Qual foi o faturamento do Q3?",
    "namespace": "statum",
    "conversation_id": "uuid-opcional",
    "stream": false
  }
  ```
- **Processo**: executa o fluxo LangGraph completo (7 nós)
- **Output**:
  ```json
  {
    "response": "O faturamento do Q3 foi de R$ 2.3M...",
    "sources": [
      {
        "document": "DRE 2025 Senior.PDF",
        "chunk": "trecho relevante...",
        "page": 3,
        "similarity": 0.89
      }
    ],
    "conversation_id": "uuid",
    "metadata": {
      "tools_used": ["vector_search"],
      "tokens_used": 2340,
      "processing_time_ms": 1800
    }
  }
  ```

### POST `/api/v1/chat/message/stream`
- Mesmo input, mas retorna SSE (Server-Sent Events) com streaming da resposta
- Cada chunk: `data: {"type": "token", "content": "O"}`
- Final: `data: {"type": "done", "sources": [...]}`

### GET `/api/v1/chat/history`
- **Input**: conversation_id + namespace
- **Output**: histórico de mensagens da conversa

---

## 4. Fluxo LangGraph (7 Nós)

Conforme o diagrama do usuário:

### Nó 1 — Planner / Task Decomposer
- **Entrada**: mensagem do usuário + histórico da conversa
- **Processo**: Gemini analisa a intenção, quebra em sub-tarefas se necessário, define plano de execução
- **Saída**: lista de sub-tarefas com tipo (knowledge_query, data_query, web_search)
- **Exemplo**: "Compare o faturamento do Q2 com o Q3" → [buscar_faturamento_Q2, buscar_faturamento_Q3, comparar]

### Nó 2 — Multi-vector RAG Search
- **Entrada**: query (ou sub-query do planner)
- **Processo**:
  - Gera embedding da query com Gemini text-embedding-004
  - Busca no pgvector filtrando por namespace
  - Recupera chunks filho (por similaridade) → retorna chunks pai (mais contexto)
  - Top-K configurável (default: 8)
- **Saída**: lista de chunks pai com scores de similaridade

### Nó 3 — Context Grader & Filter
- **Entrada**: chunks recuperados + query original
- **Processo**: Gemini avalia a relevância de cada chunk (0-10)
  - Score >= 7 → contexto OK, segue para nó 5
  - Score < 7 para todos → contexto fraco, vai para nó 4 (refina busca)
- **Saída**: chunks filtrados + flag de qualidade

### Nó 4 — Tool Executor
- **Entrada**: query + contexto atual (pode ser fraco)
- **Ferramentas disponíveis**:
  - `vector_search`: nova busca vetorial com query reformulada
  - `sql_query`: executa SQL via DuckDB em fontes estruturadas (Excel/CSV em Parquet)
  - `web_search`: busca na web (opcional, para contexto externo)
- **Processo**: Gemini decide qual tool usar com base na query e no que falta
- **Saída**: resultados adicionais das tools

### Nó 5 — Reasoning & Synthesis
- **Entrada**: todo o contexto consolidado (chunks RAG + resultados de tools)
- **Processo**:
  - Gemini faz chain-of-thought sobre o contexto
  - Detecta lacunas: se informação crítica está faltando → vai para nó 6
  - Se contexto suficiente → gera resposta
- **Saída**: resposta rascunho + flag de completude

### Nó 6 — Query Refiner
- **Entrada**: query original + lacunas detectadas
- **Processo**: reformula a query para buscar o que falta
- **Saída**: nova query → volta ao nó 2 (máximo 2 iterações)

### Nó 7 — Multi-modal Response
- **Entrada**: resposta final + chunks usados
- **Processo**:
  - Formata resposta com citações e fontes
  - Se dados tabulares envolvidos, pode gerar tabela formatada
  - Adiciona metadata (tokens, tempo, tools usadas)
- **Saída**: resposta final estruturada para o usuário

---

## 5. Regras de Negócio

- **Máximo de iterações de refinamento**: 2 (evita loops infinitos)
- **Top-K padrão para RAG**: 8 chunks
- **Threshold de relevância**: 7/10
- **Histórico de conversa**: últimas 10 mensagens enviadas como contexto
- **Timeout por requisição**: 60 segundos
- **Namespace obrigatório**: toda operação requer namespace

---

## 6. Modelos de Dados

### ChatMessage
```
id: UUID
conversation_id: UUID
namespace: str
role: "user" | "assistant"
content: str
sources: JSON (opcional)
metadata: JSON
created_at: datetime
```

### ConversationSummary
```
conversation_id: UUID
namespace: str
message_count: int
last_message_at: datetime
```
