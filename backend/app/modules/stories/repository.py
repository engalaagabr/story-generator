"""Story queries and persistence. Flushes are allowed; commits belong to use cases."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stories.generation_schemas import GeneratedStory
from app.modules.stories.models import Story, StoryNode


class StoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, story_id: int) -> Story | None:
        return await self.session.get(Story, story_id)

    async def list_nodes(self, story_id: int) -> list[StoryNode]:
        result = await self.session.scalars(
            select(StoryNode).where(StoryNode.story_id == story_id).order_by(StoryNode.id)
        )
        return list(result)

    async def create_generated(self, generated: GeneratedStory, session_id: str) -> Story:
        story = Story(title=generated.title, session_id=session_id)
        self.session.add(story)
        await self.session.flush()
        nodes = {
            node.id: StoryNode(
                story_id=story.id,
                content=node.content,
                is_root=node.id == generated.root_node_id,
                is_ending=node.is_ending,
                is_winning_ending=node.is_winning_ending,
                options=[],
            )
            for node in generated.nodes
        }
        self.session.add_all(nodes.values())
        await self.session.flush()
        # Model-local IDs must never be persisted as database references.
        for node in generated.nodes:
            nodes[node.id].options = [
                {"text": option.text, "node_id": nodes[option.node_id].id}
                for option in node.options
            ]
        return story
