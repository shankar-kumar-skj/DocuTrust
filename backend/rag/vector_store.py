import faiss
import numpy as np
import os
import pickle
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

VECTOR_DIM = 384

class FAISSVectorStore:
    def __init__(self, index_path: str = "./vector_store/index.faiss", metadata_path: str = "./vector_store/metadata.pkl"):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []
        self._lock = asyncio.Lock()
        self.load()
    
    def load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatIP(VECTOR_DIM)
            self.metadata = []
            logger.info("Created new FAISS index")
    
    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
    
    async def add_vectors(self, vectors: np.ndarray, metadatas: List[Dict]):
        if vectors.shape[1] != VECTOR_DIM:
            raise ValueError(f"Expected dim {VECTOR_DIM}, got {vectors.shape[1]}")
        async with self._lock:
            self.index.add(vectors)
            self.metadata.extend(metadatas)
            self.save()
    
    async def search(self, query_vector: np.ndarray, k: int = 10, tenant_id: str = None) -> List[Dict]:
        async with self._lock:
            if self.index.ntotal == 0:
                return []
            distances, indices = self.index.search(query_vector.reshape(1, -1), k)
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx == -1:
                    continue
                meta = self.metadata[idx]
                if meta.get("deleted", False):
                    continue
                if tenant_id and meta.get("tenant_id") != tenant_id:
                    continue
                results.append({
                    "chunk_id": meta.get("chunk_id"),
                    "text": meta.get("text"),
                    "metadata": meta,
                    "score": float(dist)
                })
            return results

    async def delete_by_doc_id(self, doc_id: str):
        async with self._lock:
            # Mark as deleted (soft delete) to avoid rebuilding index
            for meta in self.metadata:
                if meta.get("doc_id") == doc_id:
                    meta["deleted"] = True
            self.save()
            logger.info(f"Marked vectors for doc_id {doc_id} as deleted")

_vector_store = None
def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
    return _vector_store