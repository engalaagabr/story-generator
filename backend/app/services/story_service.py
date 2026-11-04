from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story, StoryNode
from app.schemas.story import CompleteStoryNodeResponse, CompleteStoryResponse


async def build_complete_story_tree(
    db: AsyncSession, story: Story
) -> CompleteStoryResponse:
    result = await db.scalars(
        select(StoryNode).where(StoryNode.story_id == story.id)
    )
    nodes = result.all()

    node_dict = {}
    for node in nodes:
        node_response = CompleteStoryNodeResponse(
            id=node.id,
            content=node.content,
            is_ending=node.is_ending,
            is_winning_ending=node.is_winning_ending,
            options=node.options,
        )
        node_dict[node.id] = node_response

    root_node = next((node for node in nodes if node.is_root), None)
    if not root_node:
        raise HTTPException(status_code=500, detail="Story root node not found")

    return CompleteStoryResponse(
        id=story.id,
        title=story.title,
        session_id=story.session_id,
        created_at=story.created_at,
        root_node=node_dict[root_node.id],
        all_nodes=node_dict,
    )
