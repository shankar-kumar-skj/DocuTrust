import os
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.constants import GEMINI_MODEL

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(GEMINI_MODEL)

class AnswerGenerationAgent:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def process(self, query: str, context_chunks: list) -> dict:
        context = "\n\n".join([chunk["text"] for chunk in context_chunks])
        prompt = f"""You are an AI assistant that answers questions based ONLY on the provided context. 
If the answer is not in the context, say "Information not found in uploaded documents."

Context:
{context}

Question: {query}

Answer:"""
        response = model.generate_content(prompt)
        answer = response.text.strip()
        return {
            "answer": answer,
            "used_chunks": context_chunks
        }