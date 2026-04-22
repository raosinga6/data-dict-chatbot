from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.error_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.logging_config import configure_logging
from app.middleware import LatencyMiddleware, TraceIDMiddleware
# from app.models.db import engine -- replaced with get_engine() to avoid circular import issues during startup
from app.models.db import get_engine
from app.routers import chat, schema

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("starting data-dict-chatbot", version="0.4.0", env=settings.environment)
    yield
    logger.info("shutting down")
    await get_engine().dispose()


app = FastAPI(
    title="Data Dictionary Chatbot",
    version="0.4.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# --- Middleware (added last = runs first) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID", "X-Process-Time"],
)
app.add_middleware(LatencyMiddleware)
app.add_middleware(TraceIDMiddleware)   # outermost: always runs first

# --- Exception handlers ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# --- Routers ---
app.include_router(chat.router, prefix="/api/v1")
app.include_router(schema.router, prefix="/api/v1")


@app.get("/health", tags=["ops"])
async def health_check():
    """
    Deep health: probes DB, Redis, ChromaDB.
    GKE liveness + readiness probe target.
    """
    from app.models.db import get_db
    from sqlalchemy import text

    checks = {}

    # PostgreSQL
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis (if configured)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # ChromaDB
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v2/heartbeat")
            checks["chromadb"] = "ok" if resp.status_code == 200 else f"status: {resp.status_code}"
    except Exception as e:
        checks["chromadb"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "0.4.0",
        "checks": checks,
    }