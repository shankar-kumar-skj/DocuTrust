from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.api.auth import get_current_user
from backend.database.mongodb import get_db
from backend.workflows.langgraph_flow import run_crag
from datetime import datetime, timezone

router = APIRouter()

class AskRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

@router.post("/ask")
async def ask(request: AskRequest, current_user = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    db = get_db()
    
    session_id = request.session_id
    if not session_id:
        session = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": request.query[:50],
            "messages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        result = await db.chat_sessions.insert_one(session)
        session_id = str(result.inserted_id)
    else:
        session = await db.chat_sessions.find_one({"_id": session_id, "tenant_id": tenant_id, "user_id": user_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    
    result = await run_crag(
        query=request.query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id
    )
    
    user_msg = {
        "role": "user",
        "content": request.query,
        "timestamp": datetime.now(timezone.utc)
    }
    assistant_msg = {
        "role": "assistant",
        "content": result["answer"],
        "timestamp": datetime.now(timezone.utc),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0),
        "hallucination_check": result.get("hallucination_check", "UNKNOWN")
    }
    
    await db.chat_sessions.update_one(
        {"_id": session_id},
        {"$push": {"messages": {"$each": [user_msg, assistant_msg]}},
         "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    
    return {
        "session_id": session_id,
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result["confidence"],
        "hallucination_check": result["hallucination_check"]
    }

@router.get("/history")
async def get_history(current_user = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    db = get_db()
    sessions = await db.chat_sessions.find(
        {"tenant_id": tenant_id, "user_id": user_id},
        sort=[("updated_at", -1)]
    ).to_list(length=50)
    for s in sessions:
        s["_id"] = str(s["_id"])
    return sessions

@router.get("/session/{session_id}")
async def get_session(session_id: str, current_user = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    db = get_db()
    session = await db.chat_sessions.find_one({"_id": session_id, "tenant_id": tenant_id, "user_id": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["_id"] = str(session["_id"])
    return session