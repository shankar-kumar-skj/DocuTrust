import logging
from datetime import datetime, timezone
from backend.database.mongodb import get_db

class AuditLogger:
    @staticmethod
    async def log(tenant_id: str, user_id: str, action: str, details: dict):
        db = get_db()
        await db.audit_logs.insert_one({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        })

class AgentLogger:
    @staticmethod
    async def log(tenant_id: str, session_id: str, agent_name: str, input_data: dict, output_data: dict, duration_ms: float):
        db = get_db()
        await db.agent_logs.insert_one({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "agent_name": agent_name,
            "input": input_data,
            "output": output_data,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc)
        })

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler()
        ]
    )