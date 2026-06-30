import os
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.constants import GEMINI_MODEL

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(GEMINI_MODEL)

class QueryRewriterAgent:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def process(self, original_query: str, intent: str = None) -> dict:
        prompt = f"""You are a query rewriter. Given the user's original query, rewrite it to be more specific and likely to retrieve relevant documents. 
Original query: "{original_query}"
Intent (if any): {intent}
Rewrite the query to improve retrieval. Output only the rewritten query."""
        response = model.generate_content(prompt)
        rewritten = response.text.strip()
        return {"rewritten_query": rewritten}