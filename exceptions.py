import uuid
import traceback
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError


def _safe_errors(errors: list) -> list:
    """Convert error list to JSON-safe format — stringify any non-serializable values."""
    safe = []
    for err in errors:
        safe_err = {}
        for k, v in err.items():
            try:
                import json
                json.dumps(v)
                safe_err[k] = v
            except (TypeError, ValueError):
                safe_err[k] = str(v)
        safe.append(safe_err)
    return safe


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            content     = {
                "error"      : "Validation error",
                "details"    : _safe_errors(exc.errors()),
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(request: Request, exc: PydanticValidationError):
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            content     = {
                "error"      : "Validation error",
                "details"    : _safe_errors(exc.errors()),
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        print(f"[SQLAlchemyError] {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            content     = {
                "error"      : "Database error occurred",
                "detail"     : str(exc),
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, (HTTPException, RequestValidationError, PydanticValidationError)):
            raise exc
        print(f"[UnhandledException] {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            content     = {
                "error"      : str(exc),
                "type"       : type(exc).__name__,
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )
