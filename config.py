import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

@dataclass
class GeminiConfig:
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview")

@dataclass
class DatabaseConfig:
    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "5432"))
    database: str = os.getenv("PG_DATABASE", "gestores_ia")
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class ChunkingConfig:
    parent_chunk_size: int = int(os.getenv("PARENT_CHUNK_SIZE", "1200"))
    parent_chunk_overlap: int = int(os.getenv("PARENT_CHUNK_OVERLAP", "200"))
    child_chunk_size: int = int(os.getenv("CHILD_CHUNK_SIZE", "300"))
    child_chunk_overlap: int = int(os.getenv("CHILD_CHUNK_OVERLAP", "50"))

@dataclass
class AppConfig:
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "8"))
    rag_relevance_threshold: int = int(os.getenv("RAG_RELEVANCE_THRESHOLD", "5"))
    max_refinement_iterations: int = int(os.getenv("MAX_REFINEMENT_ITERATIONS", "2"))
    conversation_history_limit: int = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))

@dataclass
class EmbeddingConfig:
    provider: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")
    voyage_model: str = os.getenv("VOYAGE_MODEL", "voyage-large-2")
    local_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

@dataclass
class MonitoringConfig:
    langchain_tracing: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "sofia-ia")

@dataclass
class Config:
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    app: AppConfig = field(default_factory=AppConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

# Instância global
config = Config()
