from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story


class StoryGenerator:
    @staticmethod
    async def generate_story(db: AsyncSession, session_id: str, theme: str) -> Story:
        """Create and add a Story and its nodes to db, then return the Story.

        The background task flushes and commits the transaction.
        """
        # TODO: Implement story generation and persist it using the async session.
        raise NotImplementedError("Story generation is not implemented yet.")
