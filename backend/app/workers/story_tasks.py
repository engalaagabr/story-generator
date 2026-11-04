import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.job import StoryJob
from app.services.story_generator import StoryGenerator

logger = logging.getLogger(__name__)


async def generate_story_task(job_id: str) -> None:
    """Own the session and transactions for a single generation job."""
    async with SessionLocal() as db:
        job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
        if job is None or job.status != "pending":
            return

        try:
            job.status = "processing"
            await db.commit()

            story = await StoryGenerator.generate_story(db, job.session_id, job.theme)
            await db.flush()

            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            await db.commit()

        except Exception as exc:
            logger.exception("Story generation failed for job %s", job_id)
            await db.rollback()
            # Reload after rollback, which expires ORM attributes.
            job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
            if job is None:
                return
            job.status = "failed"
            job.completed_at = datetime.now(UTC)
            job.error = str(exc)
            await db.commit()
