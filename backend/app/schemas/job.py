from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StoryJobBase(BaseModel):
    theme: str


class StoryJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: str
    created_at: datetime
    story_id: int | None = None
    completed_at: datetime | None = None
    error: str | None = None


class StoryJobCreate(StoryJobBase):
    pass
