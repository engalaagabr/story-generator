"""Job orchestration and transaction boundaries, independent of a task runner."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import ApplicationError
from app.modules.jobs.repository import StoryJobRepository
from app.modules.stories.generation import StoryGenerationService
from app.modules.stories.repository import StoryRepository

logger = logging.getLogger(__name__)


class StoryJobProcessor:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], generator: StoryGenerationService
    ) -> None:
        self.sessions = sessions
        self.generator = generator

    async def process(self, job_id: str) -> None:
        async with self.sessions() as session:
            jobs = StoryJobRepository(session)
            job = await jobs.claim_pending(job_id)
            if job is None:
                return
            theme, session_id = job.theme, job.session_id
            await session.commit()
            try:
                # No database transaction is held open during the model request.
                generated = await self.generator.generate(theme)
                story = await StoryRepository(session).create_generated(generated, session_id)
                await session.flush()
                await jobs.complete(job_id, story.id)
                # Story nodes, choice references and final job state commit together.
                await session.commit()
            except Exception as exc:
                logger.exception("Story generation failed for job %s", job_id)
                await session.rollback()
                public_error = (
                    str(exc)
                    if isinstance(exc, ApplicationError)
                    else "Story generation failed. Please try again."
                )
                await jobs.fail(job_id, public_error)
                await session.commit()
