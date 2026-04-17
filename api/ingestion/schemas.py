from pydantic import BaseModel
from typing import Optional, List

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    metadata: Optional[dict] = None
    chunks_count: Optional[int] = None
