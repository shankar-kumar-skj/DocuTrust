import re
import asyncio
from typing import List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from backend.rag.embeddings import get_embedding

class CitationValidationAgent:
    async def process(self, answer: str, used_chunks: List[Dict]) -> dict:
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        if not sentences:
            return {"cited_answer": answer, "citations": []}
        # Compute embeddings for all sentences and chunks
        sent_embs = await asyncio.gather(*[get_embedding(s) for s in sentences])
        chunk_texts = [c["text"] for c in used_chunks]
        chunk_embs = await asyncio.gather(*[get_embedding(t) for t in chunk_texts])
        citations = []
        for i, sent in enumerate(sentences):
            if len(chunk_embs) == 0:
                best_chunk = None
            else:
                sims = cosine_similarity([sent_embs[i]], chunk_embs)[0]
                best_idx = int(np.argmax(sims))
                best_chunk = used_chunks[best_idx] if sims[best_idx] > 0.3 else None
            citations.append({
                "sentence": sent,
                "source": best_chunk["metadata"].get("page", "unknown") if best_chunk else None,
                "chunk_id": best_chunk["chunk_id"] if best_chunk else None
            })
        cited_answer = ""
        for cit in citations:
            if cit["source"]:
                cited_answer += f"{cit['sentence']} (Source: Page {cit['source']}) "
            else:
                cited_answer += f"{cit['sentence']} "
        return {
            "cited_answer": cited_answer.strip(),
            "citations": citations
        }