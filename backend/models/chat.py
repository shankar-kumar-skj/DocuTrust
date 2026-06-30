from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = datetime.now(timezone.utc)
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    hallucination_check: Optional[str] = None

class ChatSession(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    user_id: str
    title: str
    messages: List[Message] = []
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)