import os
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger(__name__)

client = None
db = None

async def connect_to_mongo():
    global client, db
    try:
        mongo_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB_NAME", "docutrust")
        client = AsyncIOMotorClient(mongo_uri)
        db = client[db_name]
        await client.admin.command('ping')
        logger.info("MongoDB connection established")
        
        # Indexes
        await db.users.create_index("email", unique=True)
        await db.documents.create_index([("tenant_id", 1), ("uploaded_at", -1)])
        await db.documents.create_index([("tenant_id", 1), ("filename", 1)])
        await db.document_chunks.create_index([("doc_id", 1)])
        await db.chat_sessions.create_index([("tenant_id", 1), ("user_id", 1), ("updated_at", -1)])
        await db.audit_logs.create_index([("tenant_id", 1), ("timestamp", -1)])
        await db.agent_logs.create_index([("tenant_id", 1), ("timestamp", -1)])
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    if client:
        client.close()
        logger.info("MongoDB connection closed")

def get_db():
    if db is None:
        raise RuntimeError("MongoDB not connected. Call connect_to_mongo first.")
    return db