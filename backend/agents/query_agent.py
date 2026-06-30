import re
from typing import Dict, Any
from backend.core.constants import (
    INTENT_GENERAL, INTENT_POLICY, INTENT_LEAVE, INTENT_REMOTE, INTENT_COMPLIANCE
)

class QueryUnderstandingAgent:
    async def process(self, query: str) -> Dict[str, Any]:
        intent = INTENT_GENERAL
        keywords = []
        words = re.findall(r'\b\w+\b', query.lower())
        common = ["what", "when", "where", "how", "why", "can", "does", "is", "are", "do", "does"]
        keywords = [w for w in words if w not in common]
        if "policy" in query.lower() or "rule" in query.lower():
            intent = INTENT_POLICY
        elif "leave" in query.lower() or "vacation" in query.lower():
            intent = INTENT_LEAVE
        elif "remote" in query.lower() or "work from home" in query.lower():
            intent = INTENT_REMOTE
        elif "compliance" in query.lower():
            intent = INTENT_COMPLIANCE
        return {
            "intent": intent,
            "keywords": keywords,
            "original_query": query
        }