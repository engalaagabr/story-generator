from fastapi import APIRouter
from app.api.endpoints.job import router as job_router

router = APIRouter(prefix="/jobs", tags=["jobs"])

router.include_router(job_router)