from fastapi import APIRouter
from app.api.endpoints.health import router as health_router

router = APIRouter(tags=["Health"], prefix="/api")
router.include_router(health_router)