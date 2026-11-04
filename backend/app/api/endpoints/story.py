import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_session_id
from app.models.job import StoryJob
from app.schemas.job import StoryJobResponse
from app.schemas.story import CreateStoryRequest
from backend.app.workers.story_tasks import generate_story_task

router = APIRouter()


@router.post("/create", response_model=StoryJobResponse)
async def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
):
    response.set_cookie(key="session_id", value=session_id)

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id=job_id,
        session_id=session_id,
        theme=request.theme,
        status="pending",
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(generate_story_task, job_id, request.theme, session_id)

    return job
