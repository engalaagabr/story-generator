"""Map expected application failures to HTTP responses in one place."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError, ResourceNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        status_code = 404 if isinstance(exc, ResourceNotFoundError) else 500
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})
