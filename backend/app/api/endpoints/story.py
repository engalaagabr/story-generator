from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.api.dependencies import DatabaseSession, SessionId
from app.models.job import StoryJob
from app.schemas.job import StoryJobResponse
from app.schemas.story import CompleteStoryResponse, CreateStoryRequest
from app.services import job_service, story_service
from app.services.exceptions import InvalidStoryError, ResourceNotFoundError
from app.workers.story_tasks import generate_story_task

router = APIRouter(prefix="/story", tags=["Stories"])


@router.post("/create", response_model=StoryJobResponse)
async def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: SessionId,
    db: DatabaseSession,
) -> StoryJob:
    job = await job_service.create_story_job(db, session_id, request.theme)
    response.set_cookie(key="session_id", value=session_id)
    background_tasks.add_task(generate_story_task, job.job_id)
    return job


@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
async def get_complete_story(
    story_id: int,
    db: DatabaseSession,
) -> CompleteStoryResponse:
    try:
        return await story_service.get_complete_story(db, story_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
