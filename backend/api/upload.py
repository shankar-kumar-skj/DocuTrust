from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.api.auth import get_current_user
from backend.rag.chunking import process_document, delete_document_chunks
from backend.database.mongodb import get_db
from backend.services.logger import AuditLogger
import os
import uuid
import shutil
import traceback
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    doc_data = {
        "tenant_id": tenant_id,
        "filename": file.filename,
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "mime_type": file.content_type,
        "version": "1.0",
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc),
        "total_pages": None
    }
    db = get_db()
    result = await db.documents.insert_one(doc_data)
    doc_id = str(result.inserted_id)
    
    try:
        chunks = await process_document(file_path, tenant_id, doc_id)
        await db.documents.update_one(
            {"_id": result.inserted_id},
            {"$set": {"total_pages": len(chunks), "chunk_count": len(chunks)}}
        )
    except Exception as e:
        tb_str = traceback.format_exc()
        print("=" * 80)
        print(tb_str)
        print("=" * 80)
        if os.path.exists(file_path):
            os.remove(file_path)
        await db.documents.delete_one({"_id": result.inserted_id})
        raise HTTPException(status_code=500, detail=f"Processing failed:\n{tb_str}")
    
    await AuditLogger.log(tenant_id, user_id, "upload_document", {"doc_id": doc_id, "filename": file.filename})
    return {"message": "Document uploaded and processed", "document_id": doc_id}

@router.delete("/{document_id}")
async def delete_document(document_id: str, current_user = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(document_id), "tenant_id": tenant_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Delete file
    if os.path.exists(doc["file_path"]):
        os.remove(doc["file_path"])
    # Remove chunks from MongoDB and vector store
    await delete_document_chunks(document_id, tenant_id)
    await db.documents.delete_one({"_id": ObjectId(document_id)})
    await AuditLogger.log(tenant_id, user_id, "delete_document", {"doc_id": document_id})
    return {"message": "Document deleted"}