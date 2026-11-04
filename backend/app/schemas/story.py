from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoryOptionsSchema(BaseModel):
    text: str
    node_id: int | None = None


class StoryNodeBase(BaseModel):
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False


class CompleteStoryNodeResponse(StoryNodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    options: list[StoryOptionsSchema] = Field(default_factory=list)


class StoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    session_id: str | None = None


class CreateStoryRequest(BaseModel):
    theme: str


class CompleteStoryResponse(StoryBase):
    id: int
    created_at: datetime
    root_node: CompleteStoryNodeResponse
    all_nodes: dict[int, CompleteStoryNodeResponse]
