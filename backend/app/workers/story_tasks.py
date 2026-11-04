from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.job import StoryJob
from app.services.story_generator import StoryGenerator


async def generate_story_task(job_id: str, theme: str, session_id: str) -> None:
    async with SessionLocal() as db:
        job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
        if job is None:
            return

        try:
            job.status = "processing"
            await db.commit()

            story = await StoryGenerator.generate_story(db, session_id, theme)
            await db.flush()

            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            await db.commit()

        except Exception as exc:
            
            await db.rollback()
            # Reload after rollback, which expires ORM attributes.
            job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
            if job is None:
                return
            job.status = "failed"
            job.completed_at = datetime.now(UTC)
            job.error = str(exc)
            await db.commit()
