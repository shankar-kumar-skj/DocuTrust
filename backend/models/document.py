from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class DocumentChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

class Document(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    version: str = "1.0"
    uploaded_by: str
    uploaded_at: datetime = datetime.now(timezone.utc)
    chunks: List[DocumentChunk] = []
    total_pages: Optional[int] = None