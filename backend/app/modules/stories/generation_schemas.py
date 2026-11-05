"""Validate model output before writing any story data."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyText = Annotated[str, Field(min_length=1)]


class GeneratedStoryOption(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: NonEmptyText
    node_id: int


class GeneratedStoryNode(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: int
    content: NonEmptyText
    is_ending: bool
    is_winning_ending: bool
    options: list[GeneratedStoryOption] = Field(max_length=3)


class GeneratedStory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: NonEmptyText
    root_node_id: int
    nodes: list[GeneratedStoryNode] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        nodes = {node.id: node for node in self.nodes}
        if len(nodes) != len(self.nodes):
            raise ValueError("Node IDs must be unique; remove or renumber duplicate IDs")
        if self.root_node_id not in nodes:
            raise ValueError(f"The root node {self.root_node_id} must exist in nodes")

        for node in self.nodes:
            if node.is_ending:
                if node.options:
                    raise ValueError(f"Ending node {node.id} must have options=[]")
            elif node.is_winning_ending or not 2 <= len(node.options) <= 3:
                raise ValueError(
                    f"Non-ending node {node.id} must have 2-3 options and is_winning_ending=false"
                )
            if any(option.node_id not in nodes for option in node.options):
                missing = [option.node_id for option in node.options if option.node_id not in nodes]
                raise ValueError(f"Node {node.id} references missing option targets: {missing}")

        visited: set[int] = set()
        ending_depths: set[int] = set()

        def visit(node_id: int, path: tuple[int, ...]) -> None:
            if node_id in path:
                raise ValueError(f"Story paths cannot contain cycles: {(*path, node_id)}")
            depth = len(path) + 1
            if depth > 4:
                raise ValueError(
                    f"Path {(*path, node_id)} exceeds 4 levels counting the root as level 1; "
                    f"make node {path[3]} an ending or shorten this path"
                )
            visited.add(node_id)
            node = nodes[node_id]
            if node.is_ending:
                ending_depths.add(depth)
            for option in node.options:
                visit(option.node_id, (*path, node_id))

        visit(self.root_node_id, ())
        if visited != set(nodes):
            raise ValueError(
                f"Nodes {sorted(set(nodes) - visited)} are unreachable from the root; "
                "connect or remove them"
            )
        if not ending_depths or max(ending_depths) < 3:
            raise ValueError("The story must be 3-4 levels deep")
        if not any(node.is_winning_ending for node in self.nodes):
            raise ValueError("The story must have a winning ending")
        if not any(node.is_ending and not node.is_winning_ending for node in self.nodes):
            raise ValueError("The story must have a losing ending")
        return self
