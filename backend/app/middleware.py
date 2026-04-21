import time
import uuid
import structlog
from structlog.contextvars import clear_contextvars, bind_contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Injects a trace_id into every request.
    Priority: X-Trace-ID header (from caller) → generate new uuid4.
    Binds into structlog context so every log in the request carries it.
    Echoes the ID back in the response header for client-side correlation.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        clear_contextvars()                               # avoid leaking between requests
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        bind_contextvars(trace_id=trace_id)

        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


class LatencyMiddleware(BaseHTTPMiddleware):
    """
    Measures wall-clock latency and emits a structured log line per request.
    Adds X-Process-Time header (ms) for client-side observability.
    Slow threshold: log at WARNING when > 2s.
    """
    SLOW_THRESHOLD_MS = 2000

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Process-Time"] = str(elapsed_ms)

        log_fn = logger.warning if elapsed_ms > self.SLOW_THRESHOLD_MS else logger.info
        log_fn(
            "request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=elapsed_ms,
        )
        return response