from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# for background job tracking
class StoryJob(Base):
    __tablename__ = "story_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(index=True, unique=True)
    session_id: Mapped[str] = mapped_column(index=True)
    theme: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    story_id: Mapped[int | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )