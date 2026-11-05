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

    async def test_repairs_invalid_graph_with_feedback_and_preserves_original_request(self):
        invalid = json.loads(FIXTURE.read_text())
        invalid["nodes"][0]["options"][0]["node_id"] = 999
        invalid_text = json.dumps(invalid)
        provider = AsyncMock(spec=JsonGenerator)
        provider.generate_json.side_effect = [invalid_text, FIXTURE.read_text()]
        with self.assertLogs("app.modules.stories.generation", level="WARNING"):
            result = await StoryGenerationService(provider).generate("مغامرة في الفضاء بالعربية")
        self.assertEqual(len(result.nodes), 5)
        self.assertEqual(provider.generate_json.await_count, 2)
        first, correction = [call.args[0] for call in provider.generate_json.call_args_list]
        self.assertEqual(first.system_prompt, correction.system_prompt)
        self.assertEqual(first.response_schema, correction.response_schema)
        self.assertIn("مغامرة في الفضاء بالعربية", correction.user_prompt)
        self.assertIn("999", correction.user_prompt)
        self.assertIn("missing option targets", correction.user_prompt)
        self.assertIn(invalid_text, correction.user_prompt)
        self.assertIn("ENTIRE corrected story", correction.user_prompt)

    async def test_repairs_invalid_json_and_missing_fields(self):
        for output in ("not JSON", "{}"):
            with self.subTest(output=output):
                provider = AsyncMock(spec=JsonGenerator)
                provider.generate_json.side_effect = [output, FIXTURE.read_text()]
                with self.assertLogs("app.modules.stories.generation", level="WARNING"):
                    story = await StoryGenerationService(provider).generate("Space")
                self.assertEqual(len(story.nodes), 5)
                self.assertEqual(provider.generate_json.await_count, 2)

    async def test_retries_are_bounded_and_validation_logs_do_not_include_story_content(self):
        invalid = json.loads(FIXTURE.read_text())
        invalid["nodes"][0]["content"] = "PRIVATE_STORY_MARKER"
        invalid["nodes"][0]["options"][0]["node_id"] = 999
        for max_attempts in (1, 2, 3):
            with self.subTest(max_attempts=max_attempts):
                provider = AsyncMock(spec=JsonGenerator)
                provider.generate_json.return_value = json.dumps(invalid)
                with self.assertLogs("app.modules.stories.generation", level="WARNING") as logs:
                    with self.assertRaisesRegex(StoryGenerationError, "required structure"):
                        await StoryGenerationService(provider, max_attempts=max_attempts).generate(
                            "PRIVATE_THEME_MARKER"
                        )
                self.assertEqual(provider.generate_json.await_count, max_attempts)
                self.assertEqual(len(logs.records), max_attempts)
                self.assertNotIn("PRIVATE_STORY_MARKER", "\n".join(logs.output))
                self.assertNotIn("PRIVATE_THEME_MARKER", "\n".join(logs.output))

    async def test_provider_error_during_correction_is_not_retried(self):
        provider = AsyncMock(spec=JsonGenerator)
        provider.generate_json.side_effect = ["{}", GeminiError("Gemini quota exceeded.")]
        with self.assertLogs("app.modules.stories.generation", level="WARNING"):
            with self.assertRaisesRegex(StoryGenerationError, "Gemini quota exceeded"):
                await StoryGenerationService(provider, max_attempts=3).generate("Space")
        self.assertEqual(provider.generate_json.await_count, 2)

    def test_rejects_unbounded_attempt_configuration(self):
        for max_attempts in (0, -1, 4):
            with self.subTest(max_attempts=max_attempts):
                with self.assertRaises(ValueError):
                    StoryGenerationService(AsyncMock(spec=JsonGenerator), max_attempts=max_attempts)
