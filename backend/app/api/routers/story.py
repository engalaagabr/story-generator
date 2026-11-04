from fastapi import APIRouter
from app.api.endpoints.story import router as story_router

router = APIRouter(prefix="/story", tags=["story"])
router.include_router(story_router)
