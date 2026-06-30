import os
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.constants import GEMINI_MODEL, VERDICT_SAFE, VERDICT_HALLUCINATION

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(GEMINI_MODEL)

class HallucinationDetector:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def process(self, query: str, answer: str, context_chunks: list) -> dict:
        context = "\n\n".join([chunk["text"] for chunk in context_chunks])
        prompt = f"""You are a hallucination checker. Compare the answer against the provided context.
Determine if the answer is supported by the context. 
Respond with only "SAFE" if all claims are supported, or "HALLUCINATION" if any information is not supported.
Context:
{context}

Answer: {answer}

Verdict:"""
        response = model.generate_content(prompt)
        verdict = response.text.strip().upper()
        is_hallucination = VERDICT_HALLUCINATION in verdict
        return {
            "verdict": verdict,
            "is_hallucination": is_hallucination
        }