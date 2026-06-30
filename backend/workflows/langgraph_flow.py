import asyncio
import time
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from backend.agents.query_agent import QueryUnderstandingAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.grading_agent import RelevanceGradingAgent
from backend.agents.rewrite_agent import QueryRewriterAgent
from backend.agents.answer_agent import AnswerGenerationAgent
from backend.agents.citation_agent import CitationValidationAgent
from backend.agents.hallucination_agent import HallucinationDetector
from backend.services.logger import AgentLogger, AuditLogger

class CRAGState(TypedDict):
    query: str
    tenant_id: str
    user_id: str
    session_id: str
    intent: Dict
    retrieval_results: Dict
    graded_results: Dict
    rewritten_query: str
    answer: str
    cited_answer: str
    hallucination_check: Dict
    final_response: Dict
    retry_count: int
    max_retries: int
    used_chunks_for_answer: List

query_agent = QueryUnderstandingAgent()
retrieval_agent = RetrievalAgent()
grading_agent = RelevanceGradingAgent()
rewriter_agent = QueryRewriterAgent()
answer_agent = AnswerGenerationAgent()
citation_agent = CitationValidationAgent()
hallucination_agent = HallucinationDetector()

async def analyze_query(state: CRAGState) -> CRAGState:
    start = time.time()
    intent = await query_agent.process(state["query"])
    state["intent"] = intent
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="QueryUnderstanding",
        input_data={"query": state["query"]},
        output_data=intent,
        duration_ms=(time.time()-start)*1000
    )
    return state

async def retrieve_documents(state: CRAGState) -> CRAGState:
    start = time.time()
    query_to_use = state.get("rewritten_query") or state["query"]
    retrieval = await retrieval_agent.process(
        query=query_to_use,
        tenant_id=state["tenant_id"],
        top_k=10
    )
    state["retrieval_results"] = retrieval
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="Retrieval",
        input_data={"query": query_to_use},
        output_data={"chunk_count": len(retrieval.get("chunks", []))},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def grade_relevance(state: CRAGState) -> CRAGState:
    start = time.time()
    chunks = state["retrieval_results"].get("chunks", [])
    if not chunks:
        # No chunks to grade – set empty results
        state["graded_results"] = {
            "graded_chunks": [],
            "relevant_chunks": [],
            "irrelevant_chunks": [],
            "all_relevant": False
        }
    else:
        graded = await grading_agent.process(
            query=state["query"],
            chunks=chunks,
            threshold=0.5
        )
        state["graded_results"] = graded
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="RelevanceGrading",
        input_data={"query": state["query"]},
        output_data={"relevant_count": len(state["graded_results"].get("relevant_chunks", []))},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def rewrite_query(state: CRAGState) -> CRAGState:
    start = time.time()
    state["retry_count"] = state.get("retry_count", 0) + 1
    rewritten = await rewriter_agent.process(
        original_query=state["query"],
        intent=state["intent"]["intent"]
    )
    state["rewritten_query"] = rewritten["rewritten_query"]
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="QueryRewrite",
        input_data={"original": state["query"]},
        output_data={"rewritten": rewritten["rewritten_query"]},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def generate_answer(state: CRAGState) -> CRAGState:
    start = time.time()
    # Get relevant chunks, fallback to all chunks, then fallback to dummy placeholder
    relevant = state["graded_results"].get("relevant_chunks", [])
    if not relevant:
        relevant = state["retrieval_results"].get("chunks", [])
    if not relevant:
        # No chunks at all – provide a dummy context so the answer agent can say "not found"
        relevant = [{"text": "No content available in the knowledge base."}]
    
    answer = await answer_agent.process(
        query=state["query"],
        context_chunks=relevant
    )
    state["answer"] = answer["answer"]
    state["used_chunks_for_answer"] = relevant
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="AnswerGeneration",
        input_data={"query": state["query"]},
        output_data={"answer_length": len(answer["answer"])},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def validate_citations(state: CRAGState) -> CRAGState:
    start = time.time()
    used_chunks = state.get("used_chunks_for_answer", [])
    if not used_chunks:
        # If no chunks, just return the answer without citations
        state["cited_answer"] = state["answer"]
        citations = []
    else:
        citations = await citation_agent.process(
            answer=state["answer"],
            used_chunks=used_chunks
        )
        state["cited_answer"] = citations["cited_answer"]
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="CitationValidation",
        input_data={"answer": state["answer"][:100]},
        output_data={"citation_count": len(citations) if citations else 0},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def detect_hallucination(state: CRAGState) -> CRAGState:
    start = time.time()
    context_for_hall = state.get("used_chunks_for_answer") or state["retrieval_results"].get("chunks", [])
    if not context_for_hall:
        context_for_hall = [{"text": "No content available."}]
    
    hallucination = await hallucination_agent.process(
        query=state["query"],
        answer=state["answer"],
        context_chunks=context_for_hall
    )
    state["hallucination_check"] = hallucination
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="HallucinationDetection",
        input_data={"query": state["query"]},
        output_data={"verdict": hallucination["verdict"]},
        duration_ms=(time.time()-start)*1000
    )
    return state

async def finalize(state: CRAGState) -> CRAGState:
    confidence = 0.5
    relevant = state["graded_results"].get("relevant_chunks", [])
    if relevant:
        avg_score = sum(c["relevance_score"] for c in relevant) / len(relevant)
        confidence = min(1.0, avg_score)
    state["final_response"] = {
        "answer": state["cited_answer"],
        "confidence": confidence,
        "hallucination_check": state["hallucination_check"]["verdict"],
        "sources": [{"chunk_id": c["chunk_id"], "score": c["relevance_score"]} for c in relevant]
    }
    await AgentLogger.log(
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
        agent_name="Finalize",
        input_data={"query": state["query"]},
        output_data=state["final_response"],
        duration_ms=0
    )
    await AuditLogger.log(
        tenant_id=state["tenant_id"],
        user_id=state["user_id"],
        action="crag_query",
        details={"query": state["query"], "hallucination": state["hallucination_check"]["verdict"]}
    )
    return state

def should_retry(state: CRAGState) -> str:
    if state["graded_results"].get("all_relevant", False):
        return "generate"
    else:
        if state.get("retry_count", 0) < state.get("max_retries", 1):
            return "rewrite"
        else:
            return "generate"

def build_crag_graph():
    workflow = StateGraph(CRAGState)
    workflow.add_node("analyze_query", analyze_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("grade", grade_relevance)
    workflow.add_node("rewrite", rewrite_query)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("citations", validate_citations)
    workflow.add_node("hallucinate", detect_hallucination)
    workflow.add_node("finalize", finalize)
    
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        should_retry,
        {
            "generate": "generate",
            "rewrite": "rewrite"
        }
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", "citations")
    workflow.add_edge("citations", "hallucinate")
    workflow.add_edge("hallucinate", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()

async def run_crag(query: str, tenant_id: str, user_id: str, session_id: str) -> Dict:
    graph = build_crag_graph()
    state = CRAGState(
        query=query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        intent={},
        retrieval_results={},
        graded_results={},
        rewritten_query="",
        answer="",
        cited_answer="",
        hallucination_check={},
        final_response={},
        retry_count=0,
        max_retries=1,
        used_chunks_for_answer=[]
    )
    start_time = time.time()
    final_state = await graph.ainvoke(state)
    duration = (time.time() - start_time) * 1000
    await AgentLogger.log(
        tenant_id=tenant_id,
        session_id=session_id,
        agent_name="CRAG_Workflow_Total",
        input_data={"query": query},
        output_data={"duration_ms": duration},
        duration_ms=duration
    )
    return final_state["final_response"]