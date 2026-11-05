from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.jobs.status import StoryJobStatus


class StoryJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: StoryJobStatus
    created_at: datetime
    story_id: int | None = None
    completed_at: datetime | None = None
    error: str | None = None
