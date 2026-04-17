import re
from agent.state import AgentState
from core.gemini import GeminiClient
from core.prompts import CONTEXT_GRADER_PROMPT
from config import config

def _parse_score(text: str) -> int | None:
    """Extrai o primeiro número inteiro do texto retornado pelo LLM."""
    match = re.search(r'\d+', text.strip())
    if match:
        return int(match.group())
    return None

def context_grader_node(state: AgentState):
    """Avalia a relevância dos chunks recuperados."""
    client = GeminiClient()
    threshold = config.app.rag_relevance_threshold
    retrieved = state.get("retrieved_chunks", [])

    graded_chunks = []
    unscored_chunks = []  # chunks que falharam no LLM grader

    for chunk in retrieved:
        prompt = f"Pergunta: {state['query']}\n\nContexto: {chunk['parent_content']}"
        score_text = client.generate(prompt, system_instruction=CONTEXT_GRADER_PROMPT)

        score = _parse_score(score_text)
        if score is not None:
            chunk["relevance_score"] = score
            if score >= threshold:
                graded_chunks.append(chunk)
        else:
            # Fallback: usa a similaridade vetorial como score (0-10)
            sim_score = round(chunk.get("similarity", 0) * 10)
            chunk["relevance_score"] = sim_score
            unscored_chunks.append(chunk)

    # Se nenhum chunk passou pelo threshold, usa fallback por similaridade vetorial
    if not graded_chunks:
        sim_threshold = threshold / 10.0  # converte para escala 0-1
        fallback = [c for c in retrieved if c.get("similarity", 0) >= sim_threshold]
        # Se ainda vazio, usa os top-3 por similaridade
        if not fallback:
            fallback = sorted(retrieved, key=lambda c: c.get("similarity", 0), reverse=True)[:3]
        for c in fallback:
            if "relevance_score" not in c:
                c["relevance_score"] = round(c.get("similarity", 0) * 10)
        graded_chunks = fallback

    return {
        "graded_chunks": graded_chunks,
        "current_node": "context_grader"
    }
