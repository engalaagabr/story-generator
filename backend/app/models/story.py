from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ForeignKey, JSON, func, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    session_id: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    nodes: Mapped[list[StoryNode]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )


class StoryNode(Base):
    __tablename__ = "story_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    content: Mapped[str] = mapped_column(String)
    is_root: Mapped[bool] = mapped_column(default=False)
    is_ending: Mapped[bool] = mapped_column(default=False)
    is_winning_ending: Mapped[bool] = mapped_column(default=False)
    options: Mapped[list[Any]] = mapped_column(JSON, default=list)

    story: Mapped[Story] = relationship(back_populates="nodes")