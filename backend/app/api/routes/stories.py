from fastapi import APIRouter, BackgroundTasks, Response

from app.api.dependencies import (
    JobProcessorDependency,
    JobServiceDependency,
    SessionId,
    StoryServiceDependency,
)
from app.modules.jobs.schemas import StoryJobResponse
from app.modules.stories.schemas import CompleteStoryResponse, StoryCreateRequest

router = APIRouter(prefix="/story", tags=["Stories"])


@router.post("/create", response_model=StoryJobResponse)
async def create_story(
    request: StoryCreateRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: SessionId,
    jobs: JobServiceDependency,
    processor: JobProcessorDependency,
) -> StoryJobResponse:
    job = await jobs.create(session_id, request.theme)
    # Snapshot pending state before the processor modifies the job.
    result = StoryJobResponse.model_validate(job)
    response.set_cookie(key="session_id", value=session_id)
    background_tasks.add_task(processor.process, job.job_id)
    return result


@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
async def get_complete_story(
    story_id: int, stories: StoryServiceDependency
) -> CompleteStoryResponse:
    return await stories.get_complete(story_id)
