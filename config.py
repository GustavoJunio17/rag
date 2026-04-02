"""
Configurações centrais do pipeline de ingestão.
Altere conforme seu ambiente.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()


@dataclass
class ChunkingConfig:
    """Tamanhos de chunk pai e filho (em caracteres, ~4 chars ≈ 1 token)."""
    parent_chunk_size: int = 3000       # ~750 tokens (600–1200 tok range)
    parent_chunk_overlap: int = 200
    child_chunk_size: int = 800         # ~200 tokens (150–300 tok range)
    child_chunk_overlap: int = 100


@dataclass
class EmbeddingConfig:
    """Configuração do modelo de embeddings."""
    # Opções: "gemini", "openai", "voyage", "local"
    provider: str = "gemini"

    # Google Gemini
    gemini_model: str = "gemini-embedding-2-preview"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # OpenAI
    openai_model: str = "text-embedding-3-small"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Voyage (Anthropic)
    voyage_model: str = "voyage-3-lite"
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")

    # Local (sentence-transformers)
    local_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Dimensão do vetor (ajuste conforme o modelo)
    dimensions: int = 3072  # gemini-embedding-2-preview = 3072


@dataclass
class DatabaseConfig:
    """Configuração do PostgreSQL + pgvector."""
    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "5432"))
    database: str = os.getenv("PG_DATABASE", "gestores_ia")
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class StorageConfig:
    """Configuração do blob storage para arquivos originais."""
    # Para dev local, usa sistema de arquivos
    # Para prod, Azure Blob Storage
    provider: str = "local"  # "local" ou "azure"
    local_path: str = "./raw-docs"
    azure_connection_string: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    azure_container: str = "raw-docs"


@dataclass
class Config:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


# Instância global
config = Config()
