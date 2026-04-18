from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language question from the BA",
        examples=["Show me total revenue by region for Q1 2024"],
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for conversation continuity",
    )
    schema_filter: Optional[str] = Field(
        None,
        description="Limit search to a specific schema: Sales | HR | Finance",
    )


class RetrievedContext(BaseModel):
    table_name: str
    schema_name: str
    column_name: str
    description: str
    data_type: str
    relevance_score: float = 0.0


class JoinSuggestion(BaseModel):
    from_table: str
    to_table: str
    join_key: str
    join_type: str = "INNER"
    description: str = ""


class ChatResponse(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question: str
    sql: str
    explanation: str
    retrieved_context: list[RetrievedContext] = []
    join_suggestions: list[JoinSuggestion] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TableInfo(BaseModel):
    table_name: str
    schema_name: str
    description: str
    row_count: Optional[int] = None


class ColumnInfo(BaseModel):
    column_name: str
    table_name: str
    schema_name: str
    data_type: str
    description: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references_table: Optional[str] = None
    references_column: Optional[str] = None


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: str = Field(..., pattern="^(good|bad)$")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    trace_id: str