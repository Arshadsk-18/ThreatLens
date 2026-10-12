"""Middleware and global exception handlers.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 5.6, 10
"""

import logging
import uuid
from contextvars import ContextVar

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.errors import AppException
from app.schemas.enums import ApiErrorCode
from app.schemas.error import ErrorBody, ErrorDetail, ErrorEnvelope

logger = logging.getLogger("threatlens.api")

request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="")


def get_current_request_id() -> str:
    """Return the current context request_id or generate a new one."""
    rid = request_id_ctx.get()
    return rid or str(uuid.uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has an X-Request-ID attached and propagated."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        raw_header = request.headers.get("X-Request-ID")
        if raw_header and len(raw_header.strip()) > 0:
            req_id = raw_header.strip()
        else:
            req_id = str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions using the standard envelope."""
    req_id = get_current_request_id()
    payload = ErrorEnvelope(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=req_id,
        )
    )
    headers = {"X-Request-ID": req_id, **exc.headers}
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors with field-level details."""
    req_id = get_current_request_id()

    details: list[ErrorDetail] = []
    is_json_decode_error = False

    for err in exc.errors():
        err_type = err.get("type", "")
        if "json_invalid" in err_type or "json" in err_type.lower():
            is_json_decode_error = True

        loc = err.get("loc", ())
        field_parts = [str(part) for part in loc if part != "body"]
        field_str = ".".join(field_parts) if field_parts else None
        issue_str = err.get("msg", "Invalid value")

        details.append(ErrorDetail(field=field_str, issue=issue_str))

    # Per section 10: malformed JSON -> 400 with VALIDATION_ERROR
    status_code = 400 if is_json_decode_error else 422

    payload = ErrorEnvelope(
        error=ErrorBody(
            code=ApiErrorCode.VALIDATION_ERROR,
            message="Invalid fields.",
            details=details,
            request_id=req_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": req_id},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard Starlette/FastAPI HTTP exceptions."""
    req_id = get_current_request_id()

    # Map status code to contract ApiErrorCode
    code_map = {
        400: ApiErrorCode.VALIDATION_ERROR,
        401: ApiErrorCode.UNAUTHORIZED,
        404: ApiErrorCode.NOT_FOUND,
        409: ApiErrorCode.CONFLICT,
        422: ApiErrorCode.VALIDATION_ERROR,
        429: ApiErrorCode.RATE_LIMITED,
        500: ApiErrorCode.INTERNAL_ERROR,
    }
    code = code_map.get(exc.status_code, ApiErrorCode.INTERNAL_ERROR)

    payload = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=str(exc.detail) if exc.detail else "An error occurred.",
            details=[],
            request_id=req_id,
        )
    )
    headers = {"X-Request-ID": req_id}
    if exc.headers:
        headers.update(exc.headers)

    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler ensuring no stack traces leak to users."""
    req_id = get_current_request_id()
    logger.exception("Unhandled server exception occurred: %s", exc)

    payload = ErrorEnvelope(
        error=ErrorBody(
            code=ApiErrorCode.INTERNAL_ERROR,
            message="An internal error occurred.",
            details=[],
            request_id=req_id,
        )
    )
    return JSONResponse(
        status_code=500,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": req_id},
    )
