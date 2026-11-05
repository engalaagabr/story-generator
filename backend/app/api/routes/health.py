from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.dependencies import DatabaseSession
from app.db.health import is_database_ready

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check application and database health")
async def health(db: DatabaseSession) -> JSONResponse:
    """Report readiness without exposing connection details or exception text."""
    if not await is_database_ready(db):
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable"},
        )
    return JSONResponse(content={"status": "ok", "database": "ok"})
