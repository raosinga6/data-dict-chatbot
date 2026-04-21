import time
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.retriever import retrieve

from app.models.db import get_db
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)

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
    "[STUB] Mock response. "
    "Real RAG pipeline wires in on Day 9. "
    "Real LLM integration on Day 6."
)


async def _audit_log(question: str, session_id: str) -> None:
    logger.info("chat audit", session_id=session_id, msg_len=len(question))


async def _persist_feedback(trace_id: str, rating: str, db: AsyncSession) -> None:
    try:
        logger.info("persisting feedback", trace_id=trace_id, rating=rating)
    except Exception:
        logger.exception("feedback persistence failed", trace_id=trace_id)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    start = time.perf_counter()
    background_tasks.add_task(_audit_log, request.question, request.session_id)
    # RAG retrieval
    context = retrieve(
        question=request.question,
        schema_filter=request.schema_filter,
        top_k=8,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    return ChatResponse(
        trace_id=str(uuid.uuid4()),
        session_id=request.session_id,
        question=request.question,
        sql=_STUB_SQL,
        explanation=_STUB_EXPLANATION,
        retrieved_context=context,
        join_suggestions=[],
        confidence=0.0,
        latency_ms=latency_ms,
    )


@router.post("/feedback", response_model=FeedbackResponse, status_code=202)
async def feedback_endpoint(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    background_tasks.add_task(_persist_feedback, request.trace_id, request.rating, db)
    return FeedbackResponse(status="received", trace_id=request.trace_id)