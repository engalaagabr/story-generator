from fastapi import APIRouter
from app.api.routers.story import router as story_router

router = APIRouter(prefix="/story", tags=["story"])
router.include_router(story_router)
