# Day 4 — FastAPI Backend Scaffold (Production Hardening)

> Goal: Turn the Day 1-3 scaffold into a backend you can show a Head of Agentic AI / Head of Data Engineering hiring panel. Structured JSON logs with a trace_id, latency middleware, a clean error-envelope contract, stronger validation, background-task plumbing, and a real pytest suite against the async endpoints.

---

## 0. Why this day matters for the role

A Head-of role reviewer will skim your backend for five signals:

1. **Observability** — can you find one request across logs, metrics, traces?
2. **Error contract** — is there a single, stable error envelope clients can rely on?
3. **Validation** — is bad input rejected at the edge, not in the DB?
4. **Concurrency hygiene** — are you doing work off the request path where appropriate?
5. **Tests** — do the happy and sad paths actually run in CI?

Everything below maps to one of those five signals. Keep the mapping in your README; it is a hiring-grade artifact.

---

## 1. Dependencies

Append to `backend/requirements.txt`:

```txt
structlog==24.4.0
orjson==3.10.7
python-json-logger==2.0.7
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
anyio==4.6.0
asgi-lifespan==2.1.0
freezegun==1.5.1
```

Rebuild once: `docker compose build backend && docker compose up -d`.

---

## 2. Target file tree after Day 4

```
backend/app/
├── core/
│   ├── __init__.py
│   ├── logging.py          ← structlog config + contextvars
│   ├── middleware.py       ← trace_id + latency + access log
│   ├── exceptions.py       ← AppError hierarchy + handlers
│   └── tasks.py            ← BackgroundTasks helpers
├── config.py               ← +LOG_LEVEL, +LOG_JSON, +ENVIRONMENT
├── main.py                 ← rewired to core/*
├── models/
├── routers/
│   ├── chat.py             ← uses AppError + BackgroundTasks
│   └── schema.py           ← tighter Query() constraints
backend/tests/
├── conftest.py             ← async client + db override
├── test_health.py
├── test_schema.py
├── test_chat.py
└── test_middleware.py
```

---

## 3. Part 1 — Structured logging with `structlog`

### 3.1 Why structlog over stdlib

`logging` gives you strings. `structlog` gives you events with key/value pairs, which is what Loki / Cloud Logging / Datadog actually index. The killer feature is `contextvars.bind_contextvars(...)` — you bind `trace_id` once in middleware and every log line in that request inherits it, even from code that has no idea the trace exists.

### 3.2 `backend/app/core/logging.py`

```python
import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog + stdlib logging so they emit the same format.

    - json_logs=True for production (one JSON object per line).
    - json_logs=False for local dev (pretty colored console).
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,   # pulls trace_id in automatically
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        timestamper,
    ]

    if json_logs:
        shared_processors.append(structlog.processors.dict_tracebacks)
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())

    # Route uvicorn/sqlalchemy through our handler instead of their defaults
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    # Silence uvicorn access — we emit our own access log in middleware
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

### 3.3 Config additions (`backend/app/config.py`)

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"                     # dev | test | prod
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False                       # flip to True in prod
    CORS_ORIGINS: list[str] = ["http://localhost:8501"]
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

In `docker-compose.yaml`, set `LOG_JSON=false` for the backend service locally; set it to `true` in your k8s manifest when you get to Day 18.

---

## 4. Part 2 — Middleware: trace_id, latency, access log

A single middleware gives you: a UUID trace_id (or honors an inbound `X-Request-ID`), binds it to the log context, times the handler, echoes the id back in the response header, and writes a single structured access log per request.

### 4.1 `backend/app/core/middleware.py`

```python
import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger("access")

TRACE_HEADER = "X-Request-ID"
LATENCY_HEADER = "X-Process-Time-ms"


class TraceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        clear_contextvars()
        trace_id = request.headers.get(TRACE_HEADER) or str(uuid.uuid4())
        request.state.trace_id = trace_id

        bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return self._decorate(response, trace_id, start)
        except Exception:
            # The exception handler in exceptions.py will format the body;
            # we still log it here with the bound context.
            logger.exception("request_failed")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
            clear_contextvars()

    @staticmethod
    def _decorate(response: Response, trace_id: str, start: float) -> Response:
        response.headers[TRACE_HEADER] = trace_id
        response.headers[LATENCY_HEADER] = f"{(time.perf_counter() - start) * 1000:.2f}"
        return response
```

### 4.2 Why `BaseHTTPMiddleware` and not pure ASGI?

Pure ASGI middleware is faster but ugly for streaming bodies. For a Day-4 scaffold the `BaseHTTPMiddleware` cost (≈50 µs/req) is fine. When you profile on Day 20 and it matters, port this to a pure ASGI `__call__` — the contract stays the same.

---

## 5. Part 3 — Error handling: one envelope, many exceptions

### 5.1 The contract

Every error response looks like this:

```json
{
  "error": {
    "code": "not_found",
    "message": "Table 'sales.ordrs' not found",
    "trace_id": "3d1c6b0e-5a4e-4c8a-9c34-1f9f4c3a2b10",
    "details": { "table": "sales.ordrs" }
  }
}
```

Clients (the Streamlit UI, future React front-end, curl) only need to read `error.code` to branch behavior. `trace_id` closes the loop between the UI toast and your logs.

### 5.2 `backend/app/core/exceptions.py`

```python
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, *, details: Any = None):
        if message:
            self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "Validation failed"


class DatabaseError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "database_unavailable"
    message = "Database error"


class LLMError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_llm_error"
    message = "LLM provider failure"


def _envelope(
    trace_id: str | None,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {"code": code, "message": message, "trace_id": trace_id}
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        trace_id = getattr(request.state, "trace_id", None)
        logger.warning("app_error", code=exc.code, message=exc.message, details=exc.details)
        return _envelope(trace_id, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        trace_id = getattr(request.state, "trace_id", None)
        logger.info("request_validation_error", errors=exc.errors())
        return _envelope(
            trace_id,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException):
        trace_id = getattr(request.state, "trace_id", None)
        return _envelope(trace_id, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqla(request: Request, exc: SQLAlchemyError):
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("sqlalchemy_error")
        return _envelope(
            trace_id,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "Database error",
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("unhandled_exception")
        return _envelope(
            trace_id,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred",
        )
```

### 5.3 Using it in a router

```python
# backend/app/routers/schema.py (fragment)
from app.core.exceptions import NotFoundError

@router.get("/tables/{schema}/{name}")
async def get_table(schema: str, name: str, db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(DDTable).where(DDTable.schema_name == schema, DDTable.table_name == name)
    )
    if not row:
        raise NotFoundError(
            f"Table '{schema}.{name}' not found",
            details={"schema": schema, "table": name},
        )
    return row
```

---

## 6. Part 4 — Request & response validation

Pydantic v2 is already installed. Three upgrades make your schemas hiring-grade.

### 6.1 Tight query parameters

```python
# backend/app/routers/schema.py
from typing import Annotated
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/v1", tags=["schema"])

@router.get("/tables")
async def list_tables(
    schema: Annotated[str | None, Query(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
):
    ...
```

That `pattern` kills a whole class of SQL-identifier injection before it reaches your DB.

### 6.2 Response models for contract stability

```python
# backend/app/models/schemas.py additions
from pydantic import BaseModel, Field, ConfigDict

class ErrorEnvelope(BaseModel):
    code: str
    message: str
    trace_id: str | None = None
    details: dict | list | None = None

class ErrorResponse(BaseModel):
    error: ErrorEnvelope

class Paginated[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
```

Wire it on the endpoint:

```python
@router.get("/tables", response_model=Paginated[TableInfo],
            responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
```

Your OpenAPI schema now documents the error shape — useful when someone pastes your repo URL and opens `/docs`.

### 6.3 Field validators for the chat payload

```python
# backend/app/models/schemas.py
from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)
    include_sql: bool = True

    @field_validator("message")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be blank")
        return v
```

---

## 7. Part 5 — Background tasks

Day 4 scope is only FastAPI's built-in `BackgroundTasks`. You'll swap to `arq` (Redis) or Celery on Day 11 when RAG ingestion needs real queues. Keep the abstraction thin so the swap is mechanical.

### 7.1 `backend/app/core/tasks.py`

```python
import structlog
from app.models.schemas import FeedbackRequest

logger = structlog.get_logger(__name__)


async def record_feedback(feedback: FeedbackRequest, trace_id: str | None) -> None:
    """Placeholder: later, push to Redis Stream / BigQuery.

    Keep this idempotent and short. BackgroundTasks run in the same event
    loop as the request, so a 3s task blocks one worker's next request.
    """
    logger.info(
        "feedback_recorded",
        feedback_trace_id=trace_id,
        rating=feedback.rating,
        session_id=feedback.session_id,
    )


async def warm_schema_cache() -> None:
    logger.info("schema_cache_warm_requested")
```

### 7.2 Using it in the chat router

```python
# backend/app/routers/chat.py
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from app.core.tasks import record_feedback
from app.models.schemas import ChatRequest, ChatResponse, FeedbackRequest

router = APIRouter(prefix="/v1", tags=["chat"])

@router.post("/feedback", status_code=202)
async def submit_feedback(
    payload: FeedbackRequest,
    background: BackgroundTasks,
    request: Request,
):
    trace_id = getattr(request.state, "trace_id", None)
    background.add_task(record_feedback, payload, trace_id)
    return {"status": "accepted", "trace_id": trace_id}
```

Returning 202 is deliberate: the client sees the task was queued, not completed. That distinction is the single most common interview follow-up on background tasks.

### 7.3 When to NOT use `BackgroundTasks`

- Work that must survive a worker crash → Redis/arq/Celery.
- Work longer than a few seconds → dedicated worker.
- Work that runs on a schedule → APScheduler or k8s CronJob.

Write these three lines into your README — it's a cheap way to show you know the boundaries.

---

## 8. Part 6 — Rewired `main.py`

```python
# backend/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import TraceContextMiddleware
from app.routers import chat, schema

settings = get_settings()
configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.LOG_JSON)
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", env=settings.ENVIRONMENT, version=app.version)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="Data Dictionary Chatbot API",
    version="0.4.0",
    lifespan=lifespan,
    default_response_class=None,     # let orjson take over later
)

# ORDER MATTERS: TraceContext must wrap CORS so preflight failures get a trace_id.
app.add_middleware(TraceContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-ms"],
)

register_exception_handlers(app)

app.include_router(schema.router)
app.include_router(chat.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": app.version, "env": settings.ENVIRONMENT}
```

Middleware ordering gotcha: Starlette applies middleware in reverse add order. `TraceContextMiddleware` is added first so it runs *outermost* — every CORS response, even 400 preflights, still gets an `X-Request-ID`. Mention this in a code comment; reviewers look for this.

---

## 9. Part 7 — Testing (the single largest credibility lever)

Targets:

- `GET /health` — smoke + trace-id echo
- `GET /v1/tables` — pagination, pattern rejection
- `GET /v1/tables/{schema}/{name}` — 200 and 404 envelope
- `GET /v1/columns`, `/v1/joins`
- `POST /v1/chat` — validation errors, happy-path stub
- `POST /v1/feedback` — 202 and background task fires
- Middleware — trace_id inbound is honored, latency header present

### 9.1 `backend/tests/conftest.py`

```python
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/datadict_test",
)

from app.main import app           # noqa: E402  (env must be set first)
from app.models.db import Base, get_db   # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

Why `ASGITransport` instead of spinning uvicorn? Faster (~5x), no port contention in CI, honors `lifespan` via a context manager.

### 9.2 `backend/tests/test_health.py`

```python
import pytest

@pytest.mark.asyncio
async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"

@pytest.mark.asyncio
async def test_trace_id_generated_when_absent(client):
    r = await client.get("/health")
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Process-Time-ms")

@pytest.mark.asyncio
async def test_trace_id_honored_when_provided(client):
    r = await client.get("/health", headers={"X-Request-ID": "fixed-id-42"})
    assert r.headers["X-Request-ID"] == "fixed-id-42"
```

### 9.3 `backend/tests/test_schema.py`

```python
import pytest

@pytest.mark.asyncio
async def test_list_tables_happy_path(client):
    r = await client.get("/v1/tables?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and isinstance(body["items"], list)
    assert body["limit"] == 5

@pytest.mark.asyncio
async def test_list_tables_invalid_schema_rejected(client):
    r = await client.get("/v1/tables?schema=1bad-name")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"

@pytest.mark.asyncio
async def test_table_detail_404_envelope(client):
    r = await client.get("/v1/tables/sales/does_not_exist")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found"
    assert err["trace_id"]
```

### 9.4 `backend/tests/test_chat.py`

```python
import pytest

@pytest.mark.asyncio
async def test_chat_blank_message_rejected(client):
    r = await client.post("/v1/chat", json={"message": "   "})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"

@pytest.mark.asyncio
async def test_chat_oversized_rejected(client):
    r = await client.post("/v1/chat", json={"message": "x" * 2001})
    assert r.status_code == 422

@pytest.mark.asyncio
async def test_feedback_accepted(client):
    payload = {"session_id": "s1", "message_id": "m1", "rating": 1}
    r = await client.post("/v1/feedback", json=payload)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "accepted"
    assert body["trace_id"]
```

### 9.5 `backend/tests/test_middleware.py`

```python
import pytest

@pytest.mark.asyncio
async def test_latency_header_is_float(client):
    r = await client.get("/health")
    latency = float(r.headers["X-Process-Time-ms"])
    assert latency >= 0

@pytest.mark.asyncio
async def test_error_envelope_has_trace_id(client):
    r = await client.get("/v1/tables/sales/does_not_exist")
    body = r.json()
    assert body["error"]["trace_id"] == r.headers["X-Request-ID"]
```

The last test is the one you'll point to in your README: **the trace_id in the error body equals the trace_id in the response header, which equals the one in the logs.** That single invariant is the observability story.

### 9.6 Running

```bash
# pyproject or setup.cfg
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra -q --cov=app --cov-report=term-missing --cov-fail-under=80"
testpaths = ["backend/tests"]
```

```bash
docker compose exec backend pytest
```

Target: **80%+ line coverage** on `app/core/*` and `app/routers/*`.

Add to `cloudbuild-pr.yaml` as the first step; your PR pipeline already builds the image, so just insert a `pytest` step that reuses the built container.

---

## 10. Smoke test the whole thing

```bash
# 1. Start stack
docker compose up -d

# 2. Hit health; confirm headers
curl -i http://localhost:8000/health
# expect: X-Request-ID: <uuid>, X-Process-Time-ms: <float>

# 3. Hit known 404; confirm envelope + same trace_id across log + body + header
TRACE=$(uuidgen)
curl -s -H "X-Request-ID: $TRACE" \
     http://localhost:8000/v1/tables/sales/does_not_exist | jq
docker compose logs backend | grep "$TRACE"

# 4. Send bad chat; confirm 422 envelope
curl -s -X POST http://localhost:8000/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"message": ""}' | jq

# 5. Feedback async
curl -i -X POST http://localhost:8000/v1/feedback \
     -H "Content-Type: application/json" \
     -d '{"session_id":"s1","message_id":"m1","rating":1}'
# expect HTTP/1.1 202
```

---

## 11. Day 4 acceptance checklist

Copy into `docs/Day04_checklist.md` and tick as you go.

- [ ] `core/logging.py` configured; JSON logs in prod, console in dev
- [ ] Every request log line carries `trace_id`, `method`, `path`, `status_code`, `duration_ms`
- [ ] `TraceContextMiddleware` added *before* `CORSMiddleware`
- [ ] Incoming `X-Request-ID` honored; otherwise UUID generated
- [ ] `X-Request-ID` and `X-Process-Time-ms` present on every response
- [ ] `AppError` hierarchy defined; `NotFoundError` used in schema router
- [ ] Global handlers for `AppError`, `RequestValidationError`, `SQLAlchemyError`, `Exception`
- [ ] Every error response matches `{"error": {code, message, trace_id, details?}}`
- [ ] `ChatRequest.message` validated (non-blank, ≤2000 chars)
- [ ] `/v1/tables` uses `Query(pattern=..., ge=..., le=...)`
- [ ] `response_model` set on each list endpoint; `responses=` documents 4xx/5xx
- [ ] `BackgroundTasks` wired for `/v1/feedback`, returns 202
- [ ] `pytest-asyncio` + `httpx.AsyncClient` suite green
- [ ] ≥80% coverage on `app/core/*` and `app/routers/*`
- [ ] CI runs `pytest` in `cloudbuild-pr.yaml`
- [ ] README updated: observability story + error-envelope contract

---

## 12. Resources (in priority order)

1. FastAPI official docs — Middleware, Background Tasks, Exception Handlers:
   https://fastapi.tiangolo.com/tutorial/middleware/
   https://fastapi.tiangolo.com/tutorial/background-tasks/
   https://fastapi.tiangolo.com/tutorial/handling-errors/
2. Structlog — "Standard Library" and "Contextvars" pages are the two you must read:
   https://www.structlog.org/en/stable/standard-library.html
   https://www.structlog.org/en/stable/contextvars.html
3. Starlette middleware internals (helps the ASGI port later):
   https://www.starlette.io/middleware/
4. Pydantic v2 validators and `Annotated` query params:
   https://docs.pydantic.dev/latest/concepts/validators/
5. `httpx.AsyncClient` with `ASGITransport` for in-process tests:
   https://www.python-httpx.org/advanced/#calling-into-python-web-apps
6. "Twelve-Factor App" → logs section, to explain the JSON-to-stdout choice in interviews:
   https://12factor.net/logs
7. Tiangolo's own production-ready FastAPI template — steal ideas, not code:
   https://github.com/fastapi/full-stack-fastapi-template

---

## 13. What you'll say in an interview

> "Day 4 I locked down the API contract. Every request gets a UUID trace_id at the outermost middleware, which is bound into the structlog context so every downstream log line carries it automatically. Errors go through a single envelope — code, message, trace_id, optional details — so the Streamlit front-end, the React one we'll have later, and curl all branch on the same shape. The trace_id in the error body matches the `X-Request-ID` header and the log line, so from a user-visible toast a support engineer can find the failing request in one grep. Input validation runs at the edge using Pydantic v2 field validators and typed `Query` constraints, and schema identifiers are regex-gated before they ever hit SQL. Feedback is a 202 with `BackgroundTasks` today; on Day 11 it moves to arq behind Redis. Test coverage is pytest-asyncio against an in-process ASGI transport, currently ~85% on core and routers, wired into the PR pipeline in cloudbuild-pr.yaml."

Memorize the shape of that answer, not the words.

---

## 14. Day 5 preview

Day 5 lands the **LLM integration layer**: an abstract `LLMProvider` interface, an OpenAI-compatible implementation, retry/timeout/circuit-breaker via `tenacity`, and cost/latency capture piped into the same structlog context you built today. Everything you built on Day 4 is what makes Day 5 tractable.
