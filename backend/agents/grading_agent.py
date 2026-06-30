from sentence_transformers import CrossEncoder
import asyncio

class RelevanceGradingAgent:
    _encoder = None
    _lock = asyncio.Lock()

    async def _get_encoder(self):
        async with self._lock:
            if self._encoder is None:
                # Lazy load cross-encoder
                self._encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            return self._encoder

    async def process(self, query: str, chunks: list, threshold: float = 0.5) -> dict:
        encoder = await self._get_encoder()
        pairs = [(query, chunk["text"]) for chunk in chunks]
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, encoder.predict, pairs)
        graded = []
        for chunk, score in zip(chunks, scores):
            graded.append({
                **chunk,
                "relevance_score": float(score),
                "is_relevant": score >= threshold
            })
        relevant = [g for g in graded if g["is_relevant"]]
        return {
            "graded_chunks": graded,
            "relevant_chunks": relevant,
            "irrelevant_chunks": [g for g in graded if not g["is_relevant"]],
            "all_relevant": len(relevant) > 0
        }