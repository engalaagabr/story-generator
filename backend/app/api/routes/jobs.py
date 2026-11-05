from fastapi import APIRouter

from app.api.dependencies import JobServiceDependency
from app.modules.jobs.schemas import StoryJobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=StoryJobResponse)
async def get_job_status(job_id: str, jobs: JobServiceDependency) -> StoryJobResponse:
    return StoryJobResponse.model_validate(await jobs.get(job_id))
