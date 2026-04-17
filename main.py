from fastapi import FastAPI
from api.ingestion.router import router as ingestion_router
from api.chat.router import router as chat_router

app = FastAPI(title="RAG API para Gestores")

# Registra os routers
app.include_router(ingestion_router, prefix="/api/v1/ingestion", tags=["Ingestão"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API RAG para Gestores"}
