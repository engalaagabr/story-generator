"""Story retrieval and response assembly; SQL is owned by the repository."""

from app.core.exceptions import InvalidStoryError, ResourceNotFoundError
from app.modules.stories.repository import StoryRepository
from app.modules.stories.schemas import CompleteStoryResponse, StoryNodeResponse


class StoryService:
    def __init__(self, repository: StoryRepository) -> None:
        self.repository = repository

    async def get_complete(self, story_id: int) -> CompleteStoryResponse:
        story = await self.repository.get(story_id)
        if story is None:
            raise ResourceNotFoundError("Story not found")
        nodes = await self.repository.list_nodes(story.id)
        root = next((node for node in nodes if node.is_root), None)
        if root is None:
            raise InvalidStoryError("Story root node not found")
        responses = {node.id: StoryNodeResponse.model_validate(node) for node in nodes}
        return CompleteStoryResponse(
            id=story.id,
            title=story.title,
            session_id=story.session_id,
            created_at=story.created_at,
            root_node=responses[root.id],
            all_nodes=responses,
        )
