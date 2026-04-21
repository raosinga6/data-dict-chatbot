import structlog
from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


def _problem_response(
    status: int,
    title: str,
    detail: str,
    trace_id: str | None = None,
    errors: list | None = None,
) -> JSONResponse:
    body = {
        "type": f"https://httpstatuses.com/{status}",
        "title": title,
        "status": status,
        "detail": detail,
        "trace_id": trace_id,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    logger.warning(
        "http exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return _problem_response(
        status=exc.status_code,
        title="Request error",
        detail=str(exc.detail),
        trace_id=trace_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    errors = [
        {"loc": " → ".join(str(l) for l in e["loc"]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    logger.warning("validation error", errors=errors, path=request.url.path)
    return _problem_response(
        status=422,
        title="Validation error",
        detail="Request body failed schema validation",
        trace_id=trace_id,
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    logger.exception("unhandled exception", exc_info=exc)   # logs full traceback
    return _problem_response(
        status=500,
        title="Internal server error",
        detail="An unexpected error occurred. Use the trace_id to locate logs.",
        trace_id=trace_id,
    )