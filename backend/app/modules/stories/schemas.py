"""Public story request/response contracts; separate from generated model output."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoryCreateRequest(BaseModel):
    theme: str


class StoryOptionResponse(BaseModel):
    text: str
    node_id: int | None = None


class StoryNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False
    options: list[StoryOptionResponse] = Field(default_factory=list)


class CompleteStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    session_id: str | None = None
    created_at: datetime
    root_node: StoryNodeResponse
    all_nodes: dict[int, StoryNodeResponse]
