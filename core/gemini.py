import os
from typing import List, Dict, Any
from google import genai
from config import config

class GeminiClient:
    """Encapsulador para interação com Google Gemini."""

    def __init__(self):
        self.api_key = config.gemini.api_key
        self.model_name = config.gemini.model
        self.embedding_model = config.gemini.embedding_model
        self._client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Gera resposta em texto com fallback de modelo."""
        models_to_try = [self.model_name, "gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]
        
        last_error = None
        for model in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                return response.text
            except Exception as e:
                print(f"Erro no modelo {model}: {e}")
                last_error = e
                continue
        
        return f"Erro ao gerar resposta (Todos os modelos falharam): {last_error}"

    def generate_json(self, prompt: str, system_instruction: str = "") -> Dict[str, Any]:
        """Gera resposta em formato JSON com fallback de modelo."""
        import json, re
        models_to_try = [self.model_name, "gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]

        for model in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json"
                    )
                )
                raw = response.text or ""
                # Remove blocos de markdown se o modelo os inserir
                raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
                return json.loads(raw)
            except Exception as e:
                print(f"Erro JSON no modelo {model}: {e}")
                continue

        return {}

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings para uma lista de textos com tratamento de erro."""
        embeddings = []
        for text in texts:
            try:
                res = self._client.models.embed_content(
                    model=self.embedding_model,
                    contents=text
                )
                embeddings.append(res.embeddings[0].values)
            except Exception as e:
                print(f"Erro ao gerar embedding: {e}")
                # Fallback para vetor de zeros (3072 dims) para não quebrar o pipeline
                embeddings.append([0.0] * 3072)
        return embeddings
