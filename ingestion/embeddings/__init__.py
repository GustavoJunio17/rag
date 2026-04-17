"""
Gerador de embeddings — suporta Gemini (padrão), OpenAI, Voyage e modelos locais.
Processa em batches para evitar rate limits.
"""

from typing import Optional
from config import config


class Embedder:
    """Gera embeddings para textos usando o provider configurado."""

    BATCH_SIZE = 50  # Gemini tem rate limit mais agressivo

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or config.embedding.provider
        self._client = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings para uma lista de textos.
        Processa em batches para evitar rate limits.
        """
        all_embeddings = []

        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """Gera embedding para uma única query (busca)."""
        result = self._embed_batch([text])
        return result[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Dispatch para o provider configurado."""
        if self.provider == "gemini":
            return self._embed_gemini(texts)
        elif self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "voyage":
            return self._embed_voyage(texts)
        elif self.provider == "local":
            return self._embed_local(texts)
        else:
            raise ValueError(f"Provider de embedding desconhecido: {self.provider}")

    # ---- Providers ----

    def _embed_gemini(self, texts: list[str]) -> list[list[float]]:
        from google import genai

        if not self._client:
            self._client = genai.Client(api_key=config.embedding.gemini_api_key)

        result = self._client.models.embed_content(
            model=config.embedding.gemini_model,
            contents=texts,
        )
        return [embedding.values for embedding in result.embeddings]

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        if not self._client:
            self._client = OpenAI(api_key=config.embedding.openai_api_key)

        response = self._client.embeddings.create(
            model=config.embedding.openai_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _embed_voyage(self, texts: list[str]) -> list[list[float]]:
        import voyageai

        if not self._client:
            self._client = voyageai.Client(api_key=config.embedding.voyage_api_key)

        result = self._client.embed(
            texts=texts,
            model=config.embedding.voyage_model,
        )
        return result.embeddings

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        from sentence_transformers import SentenceTransformer

        if not self._client:
            self._client = SentenceTransformer(config.embedding.local_model)

        embeddings = self._client.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
