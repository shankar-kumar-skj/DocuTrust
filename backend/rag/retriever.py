from backend.rag.embeddings import get_embedding
from backend.rag.vector_store import get_vector_store
from typing import List, Dict

class HybridRetriever:
    def __init__(self):
        self.vector_store = get_vector_store()
    
    async def retrieve(self, query: str, tenant_id: str, top_k: int = 10) -> List[Dict]:
        query_vec = await get_embedding(query)
        semantic_results = await self.vector_store.search(query_vec, k=top_k, tenant_id=tenant_id)
        return semantic_results