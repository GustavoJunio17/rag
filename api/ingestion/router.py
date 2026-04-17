from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from typing import List
from api.ingestion.schemas import UploadResponse, DocumentResponse
from api.deps import get_db, get_pipeline
from storage.pgvector_store import PgVectorStore
from ingestion.pipeline import IngestionPipeline

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    namespace: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: PgVectorStore = Depends(get_db),
    pipeline: IngestionPipeline = Depends(get_pipeline)
):
    # Salva o arquivo temporariamente (simplificado para MVP)
    temp_path = f"mnt/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # Processa em background (conforme especificado)
    background_tasks.add_task(pipeline.ingest, temp_path, namespace)
    
    return UploadResponse(
        doc_id="pending", # O ID real será criado no pipeline
        filename=file.filename,
        status="processing"
    )

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(namespace: str, db: PgVectorStore = Depends(get_db)):
    docs = db.get_documents(namespace)
    return [
        DocumentResponse(
            id=str(d["id"]),
            filename=d["filename"],
            status=d["status"],
            metadata=d["metadata"]
        ) for d in docs
    ]
