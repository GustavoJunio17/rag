# Sofia IA 🤖 — Advanced RAG with LangGraph

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-Latest-orange?style=for-the-badge" alt="LangGraph">
  <img src="https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

---

**Sofia IA** é um sistema inteligente de Recuperação Aumentada por Geração (RAG) projetado especificamente para gestores. Utilizando a potência do **Google Gemini** e a orquestração cíclica do **LangGraph**, a Sofia é capaz de ingerir documentos complexos e fornecer respostas precisas com contexto em tempo real.

## ✨ Destaques
- **Fluxos Cíclicos**: Orquestração via LangGraph para raciocínio em múltiplas etapas e refinamento de buscas.
- **Busca Vetorial de Alta Performance**: Integração com `pgvector` no PostgreSQL para recuperação semântica eficiente.
- **Ingestão Inteligente**: Pipeline escalável para processamento de arquivos PDF e outros documentos com namespaces.
- **REST API Moderna**: Baseada em FastAPI com documentação automática (Swagger/ReDoc).
- **Monitoramento Nativo**: Preparado para LangSmith para inspeção profunda de traces e depuração de agentes.

## 🏗️ Arquitetura do Sistema
O projeto é dividido em camadas modulares para facilitar a manutenção e escalabilidade:

1.  **Agent Layer (`agent/`)**: Define o grafo de controle, estados e lógica de decisão do assistente.
2.  **Core Layer (`core/`)**: Clientes LLM (Gemini), gerenciamento de prompts e configurações globais.
3.  **Ingestion Layer (`ingestion/`)**: Processamento e fragmentação (chunking) de documentos para o banco vetorial.
4.  **API Layer (`api/`)**: Interface REST para interação em tempo real e upload de dados.
5.  **Storage Layer (`storage/` & `db/`)**: Gerenciamento de persistência vetorial e estruturada.

## 🚀 Como Iniciar

### 1. Pré-requisitos
- Docker & Docker Compose
- Python 3.10+

### 2. Infraestrutura
Inicie o banco de dados com suporte a vetores:
```bash
docker-compose up -d
```

### 3. Configuração do Ambiente
Crie seu ambiente virtual e instale as dependências:
```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Variáveis de Ambiente
Copie o template e preencha com suas credenciais:
```bash
cp .env.example .env
```
> [!IMPORTANT]
> Certifique-se de adicionar sua `GEMINI_API_KEY` no arquivo `.env`.

### 5. Execução
**Inicie a API:**
```bash
uvicorn main:app --reload --port 8000
```
Acesse a documentação interativa em: `http://localhost:8000/docs`

**Ingestão Manual:**
```bash
python ingestion/pipeline.py --file "dados/seu-documento.pdf" --namespace "prospeccao"
```

## 📜 Licença
Este projeto está sob a licença [MIT](LICENSE).

---
<p align="center">Desenvolvido com ❤️ por <a href="https://github.com/GustavoJunio17">Gustavo Junio</a></p>
