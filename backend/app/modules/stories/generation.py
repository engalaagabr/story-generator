"""Generate and validate stories through an injected provider contract."""

from pydantic import ValidationError

from app.core.exceptions import StoryGenerationError
from app.integrations.llm.contracts import JsonGenerationRequest, JsonGenerator
from app.integrations.llm.exceptions import ModelProviderError
from app.modules.stories.generation_schemas import GeneratedStory
from app.modules.stories.prompts import build_story_prompt


class StoryGenerationService:
    def __init__(self, provider: JsonGenerator) -> None:
        self.provider = provider

    async def generate(self, theme: str) -> GeneratedStory:
        request = JsonGenerationRequest(
            system_prompt=build_story_prompt(),
            user_prompt=f"Story theme: {theme}",
            response_schema=GeneratedStory.model_json_schema(),
        )
        try:
            content = await self.provider.generate_json(request)
        except ModelProviderError as exc:
            raise StoryGenerationError(str(exc)) from None
        try:
            return GeneratedStory.model_validate_json(content)
        except ValidationError:
            raise StoryGenerationError(
                "The generated story did not match the required structure. Please try again."
            ) from None
