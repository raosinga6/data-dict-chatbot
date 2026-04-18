import time
import uuid

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Stub SQL templates — replaced by real LLM on Day 6, RAG on Day 9
# ---------------------------------------------------------------------------
_STUB_SQL = """\
SELECT
    region,
    SUM(revenue)  AS total_revenue,
    COUNT(*)      AS order_count
FROM sales.orders
WHERE order_date >= '2024-01-01'
  AND order_date <  '2024-04-01'
GROUP BY region
ORDER BY total_revenue DESC
LIMIT 1000;"""

_STUB_EXPLANATION = (
    "[STUB — Day 1] Mock response. "
    "Real RAG pipeline wires in on Day 9. "
    "Real LLM integration on Day 6."
)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    start = time.perf_counter()

    # TODO Day 9:  retrieved_context = await retriever.query(request.question)
    # TODO Day 11: join_suggestions  = join_graph.find_path(tables)
    # TODO Day 6:  sql = await llm.generate_sql(request.question, context)

    latency_ms = int((time.perf_counter() - start) * 1000)

    return ChatResponse(
        trace_id=str(uuid.uuid4()),
        session_id=request.session_id,
        question=request.question,
        sql=_STUB_SQL,
        explanation=_STUB_EXPLANATION,
        retrieved_context=[],
        join_suggestions=[],
        confidence=0.0,
        latency_ms=latency_ms,
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest) -> FeedbackResponse:
    # TODO Day 26: persist to PostgreSQL + push to LangSmith
    return FeedbackResponse(status="received", trace_id=request.trace_id)