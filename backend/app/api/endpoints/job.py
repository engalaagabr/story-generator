from fastapi import APIRouter, HTTPException

from app.api.dependencies import DatabaseSession
from app.models.job import StoryJob
from app.schemas.job import StoryJobResponse
from app.services import job_service
from app.services.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=StoryJobResponse)
async def get_job_status(job_id: str, db: DatabaseSession) -> StoryJob:
    try:
        return await job_service.get_job(db, job_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
