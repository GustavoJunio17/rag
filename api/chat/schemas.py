from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    namespace: str
    conversation_id: Optional[str] = None
    stream: bool = False

class Source(BaseModel):
    document: str
    chunk: str
    page: Optional[int] = None
    similarity: float

class ChatResponse(BaseModel):
    response: str
    sources: List[Source]
    conversation_id: str
    metadata: dict = {}
