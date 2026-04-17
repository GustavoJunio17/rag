from fastapi import APIRouter, Depends, HTTPException
from typing import List
from api.chat.schemas import ChatRequest, ChatResponse, Source
from api.deps import get_db, get_agent
from storage.pgvector_store import PgVectorStore

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest, 
    db: PgVectorStore = Depends(get_db),
    agent = Depends(get_agent)
):
    # 1. Garante que temos uma conversa válida
    conv_id = request.conversation_id
    if not conv_id or not db.conversation_exists(conv_id, request.namespace):
        conv_id = db.create_conversation(request.namespace, title=request.message[:50])
    
    # 2. Busca histórico recente
    history = db.get_chat_history(conv_id, request.namespace)
    
    # 3. Invoca o agente LangGraph
    # Converte histórico para o formato do AgentState se necessário
    agent_input = {
        "messages": history,
        "query": request.message,
        "namespace": request.namespace,
        "iteration_count": 0
    }
    
    result = agent.invoke(agent_input)
    
    # 4. Salva a interação no banco
    db.insert_chat_message(conv_id, request.namespace, "user", request.message)
    db.insert_chat_message(
        conv_id, 
        request.namespace, 
        "assistant", 
        result["final_response"],
        sources=result["sources"]
    )
    
    # 5. Formata a resposta
    sources = [
        Source(
            document=s["document"],
            chunk="", # Placeholder para compatibilidade
            page=s.get("page"),
            similarity=s.get("similarity", 0.0)
        ) for s in result["sources"]
    ]
    
    return ChatResponse(
        response=result["final_response"],
        sources=sources,
        conversation_id=conv_id,
        metadata=result.get("metadata", {})
    )

@router.get("/history")
async def get_history(namespace: str, conversation_id: str, db: PgVectorStore = Depends(get_db)):
    messages = db.get_chat_history(conversation_id, namespace)
    return messages
