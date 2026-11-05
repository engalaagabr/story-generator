"""Provider-neutral contract; no knowledge of stories, HTTP routes or persistence."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class JsonGenerationRequest:
    system_prompt: str
    user_prompt: str
    response_schema: dict[str, Any]


class JsonGenerator(Protocol):
    async def generate_json(self, request: JsonGenerationRequest) -> str:
        """Return model text; callers own JSON parsing and domain validation."""
        ...
