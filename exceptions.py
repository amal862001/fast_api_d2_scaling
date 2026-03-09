import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError


def register_exception_handlers(app: FastAPI):

    # Handle validation errors (422) 
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            content     = {
                "error"      : "Validation error",
                "details"    : exc.errors(),
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )

    # Handle database errors (500) 
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        return JSONResponse(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            content     = {
                "error"      : "Database error occurred",
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )

    # Handle all other errors (500)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            content     = {
                "error"      : str(exc),
                "request_id" : str(uuid.uuid4()),
                "timestamp"  : datetime.now(timezone.utc).isoformat()
            }
        )
    
    

