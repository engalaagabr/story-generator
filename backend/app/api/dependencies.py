import uuid
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


def get_session_id(
    session_id: Annotated[str | None, Cookie()] = None,
) -> str:
    return session_id or str(uuid.uuid4())


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
SessionId = Annotated[str, Depends(get_session_id)]
