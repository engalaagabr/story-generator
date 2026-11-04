import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import StoryJob
from app.services.exceptions import ResourceNotFoundError


async def create_story_job(
    db: AsyncSession, session_id: str, theme: str
) -> StoryJob:
    """Commit the pending job before it is handed to a background task."""
    async with db.begin():
        job = StoryJob(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            theme=theme,
            status="pending",
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> StoryJob:
    job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
    if job is None:
        raise ResourceNotFoundError("Job not found")
    return job
