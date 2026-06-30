from backend.rag.retriever import HybridRetriever

retriever = HybridRetriever()

class RetrievalAgent:
    async def process(self, query: str, tenant_id: str, top_k: int = 10) -> dict:
        results = await retriever.retrieve(query, tenant_id, top_k)
        return {
            "query": query,
            "chunks": results,
            "top_k": top_k
        }