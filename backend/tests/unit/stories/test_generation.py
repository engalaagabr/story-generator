import json
import unittest
from unittest.mock import AsyncMock

from app.core.exceptions import StoryGenerationError
from app.integrations.llm.contracts import JsonGenerator
from app.integrations.llm.exceptions import GeminiError
from app.modules.stories.generation import StoryGenerationService
from app.modules.stories.generation_schemas import GeneratedStory
from app.modules.stories.prompts import EXAMPLE_STORY
from tests.support import FIXTURE


class StoryGenerationTests(unittest.IsolatedAsyncioTestCase):
    def test_prompt_example_is_a_complete_valid_story(self):
        GeneratedStory.model_validate(EXAMPLE_STORY)

    async def test_builds_prompt_and_validates_output_without_database(self):
        provider = AsyncMock(spec=JsonGenerator)
        provider.generate_json.return_value = FIXTURE.read_text()
        story = await StoryGenerationService(provider).generate("Space {adventure}")
        self.assertEqual(len(story.nodes), 5)
        request = provider.generate_json.call_args.args[0]
        self.assertIn("choose-your-own-adventure", request.system_prompt)
        self.assertNotIn("{format_instructions}", request.system_prompt)
        self.assertEqual(request.user_prompt, "Story theme: Space {adventure}")
        self.assertIn("root_node_id", request.response_schema["properties"])

    async def test_invalid_json_schema_and_graph_are_application_errors(self):
        invalid_graph = json.loads(FIXTURE.read_text())
        invalid_graph["nodes"][0]["options"][0]["node_id"] = 999
        for content in ("not JSON", "{}", json.dumps(invalid_graph)):
            with self.subTest(content=content[:30]):
                provider = AsyncMock(spec=JsonGenerator)
                provider.generate_json.return_value = content
                with self.assertRaisesRegex(StoryGenerationError, "required structure"):
                    await StoryGenerationService(provider).generate("Space")

    async def test_safe_provider_failure_is_translated_at_feature_boundary(self):
        provider = AsyncMock(spec=JsonGenerator)
        provider.generate_json.side_effect = GeminiError("Gemini quota exceeded.")
        with self.assertRaisesRegex(StoryGenerationError, "Gemini quota exceeded"):
            await StoryGenerationService(provider).generate("Space")
        provider.generate_json.assert_awaited_once()
