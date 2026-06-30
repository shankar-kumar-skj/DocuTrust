from fastapi import APIRouter, Depends
from backend.api.auth import get_current_user
from backend.database.mongodb import get_db
from typing import Optional

router = APIRouter()

@router.get("/agent-logs")
async def get_agent_logs(
    limit: int = 50,
    session_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    db = get_db()
    filter_criteria = {"tenant_id": tenant_id}
    if session_id:
        filter_criteria["session_id"] = session_id
    logs = await db.agent_logs.find(filter_criteria, sort=[("timestamp", -1)]).to_list(length=limit)
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    user_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    db = get_db()
    filter_criteria = {"tenant_id": tenant_id}
    if user_id:
        filter_criteria["user_id"] = user_id
    logs = await db.audit_logs.find(filter_criteria, sort=[("timestamp", -1)]).to_list(length=limit)
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs