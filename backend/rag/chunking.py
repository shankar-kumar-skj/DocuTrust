import traceback
from typing import List
import logging
from backend.services.pdf_parser import extract_pdf_structure, chunk_by_structure
from backend.rag.embeddings import get_embeddings_batch
from backend.database.mongodb import get_db
from backend.models.document import DocumentChunk

logger = logging.getLogger(__name__)

async def process_document(file_path: str, tenant_id: str, doc_id: str) -> List[DocumentChunk]:
    try:
        structure = extract_pdf_structure(file_path)
        logger.info(f"Extracted PDF structure: {len(structure['pages'])} pages")
        raw_chunks = chunk_by_structure(structure, chunk_size=500, overlap=50)
        logger.info(f"Created {len(raw_chunks)} raw chunks")

        texts = [chunk["text"] for chunk in raw_chunks]
        embeddings = await get_embeddings_batch(texts)

        chunks = []
        for i, (raw, emb) in enumerate(zip(raw_chunks, embeddings)):
            safe_metadata = {}
            for k, v in raw["metadata"].items():
                if isinstance(v, (str, int, float, bool, type(None))):
                    safe_metadata[k] = v
                else:
                    safe_metadata[k] = str(v)

            chunk = DocumentChunk(
                chunk_id=f"{doc_id}_{i}",
                text=raw["text"],
                metadata={**safe_metadata, "tenant_id": tenant_id, "doc_id": doc_id},
                embedding=emb.tolist()
            )
            chunks.append(chunk)

        await store_chunks(chunks, tenant_id, doc_id)
        return chunks

    except Exception as e:
        print("=" * 80)
        print("ERROR in process_document:")
        traceback.print_exc()
        print("=" * 80)
        raise

async def store_chunks(chunks: List[DocumentChunk], tenant_id: str, doc_id: str):
    try:
        db = get_db()
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = chunk.dict()
            chunk_dict["tenant_id"] = tenant_id
            chunk_dict["doc_id"] = doc_id
            chunk_dicts.append(chunk_dict)
        if chunk_dicts:
            await db.document_chunks.insert_many(chunk_dicts)
            logger.info(f"Inserted {len(chunk_dicts)} chunks into MongoDB")

        from backend.rag.vector_store import get_vector_store
        vector_store = get_vector_store()
        vectors = []
        metadatas = []
        for chunk in chunks:
            vectors.append(chunk.embedding)
            metadatas.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "tenant_id": tenant_id,
                "doc_id": doc_id,
                **chunk.metadata
            })
        if vectors:
            import numpy as np
            vectors_np = np.array(vectors)
            await vector_store.add_vectors(vectors_np, metadatas)
            logger.info(f"Added {len(vectors)} vectors to FAISS")
    except Exception as e:
        print("=" * 80)
        print("ERROR in store_chunks:")
        traceback.print_exc()
        print("=" * 80)
        raise

async def delete_document_chunks(doc_id: str, tenant_id: str):
    db = get_db()
    # Remove from MongoDB
    await db.document_chunks.delete_many({"doc_id": doc_id, "tenant_id": tenant_id})
    # Remove from FAISS
    from backend.rag.vector_store import get_vector_store
    vector_store = get_vector_store()
    await vector_store.delete_by_doc_id(doc_id)
    logger.info(f"Deleted chunks for document {doc_id}")