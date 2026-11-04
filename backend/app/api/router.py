from fastapi import APIRouter

from app.api.endpoints import health, job, story

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(story.router)
api_router.include_router(job.router)
