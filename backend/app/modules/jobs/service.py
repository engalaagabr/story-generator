"""Create committed jobs and retrieve job state."""

from app.core.exceptions import ResourceNotFoundError
from app.modules.jobs.models import StoryJob
from app.modules.jobs.repository import StoryJobRepository


class StoryJobService:
    def __init__(self, repository: StoryJobRepository) -> None:
        self.repository = repository

    async def create(self, session_id: str, theme: str) -> StoryJob:
        # A task must never observe a job that has not been committed yet.
        async with self.repository.session.begin():
            return await self.repository.create(session_id, theme)

    async def get(self, job_id: str) -> StoryJob:
        job = await self.repository.get(job_id)
        if job is None:
            raise ResourceNotFoundError("Job not found")
        return job
