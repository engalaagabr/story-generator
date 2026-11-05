"""HTTP dependency wiring. Application services never import this module."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.processor import StoryJobProcessor
from app.modules.jobs.repository import StoryJobRepository
from app.modules.jobs.service import StoryJobService
from app.modules.stories.repository import StoryRepository
from app.modules.stories.service import StoryService


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.session_factory() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_session_id(session_id: Annotated[str | None, Cookie()] = None) -> str:
    return session_id or str(uuid4())


def get_story_service(session: DatabaseSession) -> StoryService:
    return StoryService(StoryRepository(session))


def get_job_service(session: DatabaseSession) -> StoryJobService:
    return StoryJobService(StoryJobRepository(session))


def get_job_processor(request: Request) -> StoryJobProcessor:
    return request.app.state.job_processor


SessionId = Annotated[str, Depends(get_session_id)]
StoryServiceDependency = Annotated[StoryService, Depends(get_story_service)]
JobServiceDependency = Annotated[StoryJobService, Depends(get_job_service)]
JobProcessorDependency = Annotated[StoryJobProcessor, Depends(get_job_processor)]
