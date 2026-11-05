"""Story-job SQL, including an atomic pending-to-processing claim."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import StoryJob
from app.modules.jobs.status import StoryJobStatus


class StoryJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: str) -> StoryJob | None:
        return await self.session.scalar(select(StoryJob).where(StoryJob.job_id == job_id))

    async def create(self, session_id: str, theme: str) -> StoryJob:
        job = StoryJob(
            job_id=str(uuid4()),
            session_id=session_id,
            theme=theme,
            status=StoryJobStatus.PENDING,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def claim_pending(self, job_id: str) -> StoryJob | None:
        return await self.session.scalar(
            update(StoryJob)
            .where(StoryJob.job_id == job_id, StoryJob.status == StoryJobStatus.PENDING)
            .values(status=StoryJobStatus.PROCESSING)
            .returning(StoryJob)
        )

    async def complete(self, job_id: str, story_id: int) -> None:
        await self.session.execute(
            update(StoryJob)
            .where(StoryJob.job_id == job_id)
            .values(
                status=StoryJobStatus.COMPLETED,
                story_id=story_id,
                completed_at=datetime.now(UTC),
                error=None,
            )
        )

    async def fail(self, job_id: str, error: str) -> None:
        await self.session.execute(
            update(StoryJob)
            .where(StoryJob.job_id == job_id, StoryJob.status == StoryJobStatus.PROCESSING)
            .values(
                status=StoryJobStatus.FAILED,
                story_id=None,
                completed_at=datetime.now(UTC),
                error=error,
            )
        )
