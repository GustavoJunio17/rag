# Constitution — IA para Gestores (RAG + LangGraph)

## Identidade

Este projeto é uma **API inteligente para gestores** que permite fazer perguntas sobre documentos empresariais (PDF, DOCX, Excel) usando uma IA baseada em RAG (Retrieval Augmented Generation) com orquestração via LangGraph.

## Missão

Permitir que gestores obtenham respostas precisas e fundamentadas sobre seus documentos sem precisar ler centenas de páginas. A IA deve:

1. **Entender documentos uma única vez** — ingestão processa e indexa, não reenvia a cada pergunta
2. **Buscar apenas o relevante** — RAG vetorial recupera só os trechos necessários
3. **Operar sobre dados tabulares** — queries SQL em planilhas Excel/CSV via DuckDB
4. **Citar fontes** — toda resposta indica de qual documento e trecho veio a informação
5. **Ser iterativa** — se o contexto recuperado não for suficiente, refina a busca automaticamente

## Princípios Técnicos

- **LLM**: Google Gemini (gemini-2.0-flash ou gemini-2.5-flash)
- **Embeddings**: Gemini text-embedding-004 (768 dimensões)
- **Orquestração**: LangGraph para o fluxo de raciocínio com loops condicionais
- **Banco vetorial**: PostgreSQL + pgvector
- **Dados estruturados**: DuckDB para queries SQL em Parquet
- **API**: FastAPI com endpoints REST
- **Multi-tenancy**: isolamento por namespace (cada empresa/gestor tem seu espaço)

## Restrições

- Contexto do LLM limitado a ~131k tokens por requisição — nunca enviar documentos inteiros
- A IA responde APENAS com base nos documentos do namespace — não inventa informações
- Se não encontrar resposta nos documentos, deve dizer explicitamente que não encontrou
- Dados de um namespace nunca devem vazar para outro

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- LangGraph
- Google GenAI SDK (google-genai)
- PostgreSQL 16 + pgvector
- DuckDB
- Pandas / PyArrow
