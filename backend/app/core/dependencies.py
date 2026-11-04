import uuid
from typing import Annotated

from fastapi import Cookie


def get_session_id(
    session_id: Annotated[str | None, Cookie()] = None,
) -> str:
    if not session_id:
        session_id = str(uuid.uuid4())

    return session_id