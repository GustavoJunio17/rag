# Pipeline de Ingestão — IA para Gestores

Arquitetura de ingestão de documentos com chunking hierárquico (pai/filho),
embeddings vetoriais e armazenamento em PostgreSQL + pgvector.

## Estrutura

```
ingestion_pipeline/
├── config.py              # Configurações centrais
├── requirements.txt       # Dependências
├── docker-compose.yml     # PostgreSQL + pgvector
├── db/
│   └── schema.sql         # Tabelas do banco
├── loaders/
│   ├── __init__.py
│   ├── base.py            # Interface base
│   ├── pdf_loader.py      # Extração de PDF
│   ├── docx_loader.py     # Extração de DOCX
│   ├── excel_loader.py    # Extração de XLSX/CSV → Parquet
│   └── txt_loader.py      # Leitura direta de TXT
├── chunking/
│   ├── __init__.py
│   └── hierarchical.py    # Chunking pai/filho
├── embeddings/
│   ├── __init__.py
│   └── embedder.py        # Geração de embeddings
├── storage/
│   ├── __init__.py
│   └── pgvector_store.py  # Armazenamento no pgvector
├── ingestion.py           # Orquestrador principal
└── worker.py              # Worker que escuta fila (Azure Service Bus ou local)
```

## Como rodar

1. `docker-compose up -d` — sobe o PostgreSQL com pgvector
2. `psql` e roda o `db/schema.sql`
3. `pip install -r requirements.txt`
4. `python ingestion.py --file caminho/do/arquivo --namespace empresa_x`
