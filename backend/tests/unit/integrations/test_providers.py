import json
import unittest

import httpx
from pydantic import SecretStr, ValidationError

from app.integrations.llm.contracts import JsonGenerationRequest
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.llm.exceptions import DeepSeekError, GeminiError
from app.integrations.llm.factory import create_json_generator
from app.integrations.llm.gemini import GeminiProvider
from app.integrations.llm.json_schema import simplify_gemini_schema
from tests.support import make_settings

REQUEST = JsonGenerationRequest(
    system_prompt="Return the requested data as JSON.",
    user_prompt="Extract a title and value from this input: {example}.",
    response_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1},
            "value": {"type": "integer"},
        },
        "required": ["title", "value"],
    },
)
CONTENT = '{"title":"An arbitrary JSON task","value":42}'


def deepseek_response(content=CONTENT, finish="stop"):
    return httpx.Response(
        200, json={"choices": [{"finish_reason": finish, "message": {"content": content}}]}
    )


def gemini_response(content=CONTENT, finish="STOP"):
    return httpx.Response(
        200,
        json={"candidates": [{"finishReason": finish, "content": {"parts": [{"text": content}]}}]},
    )


class ProviderTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = make_settings()
        self.requests = []

    async def generate(self, provider_type, response):
        def handler(request):
            self.requests.append(request)
            if isinstance(response, Exception):
                raise response
            return response

        provider = provider_type(self.config, transport=httpx.MockTransport(handler))
        return await provider.generate_json(REQUEST)


class DeepSeekProviderTests(ProviderTestCase):
    async def test_configured_request_and_raw_json_response(self):
        self.config.DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/"
        self.config.DEEPSEEK_MODEL = "custom-model"
        self.config.DEEPSEEK_MAX_TOKENS = 4096
        self.assertEqual(await self.generate(DeepSeekProvider, deepseek_response()), CONTENT)
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer test-deepseek-key")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "custom-model")
        self.assertEqual(
            body["messages"],
            [
                {"role": "system", "content": REQUEST.system_prompt},
                {"role": "user", "content": REQUEST.user_prompt},
            ],
        )
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["max_tokens"], 4096)
        self.assertFalse(body["stream"])

    async def test_model_alias_and_reasoning_match_endpoint(self):
        for url, model, expected, openrouter in (
            ("https://api.deepseek.com", "deepseek/deepseek-v4.1-flash", "deepseek-flash", False),
            ("https://api.deepseek.com/v1/", "deepseek-v4.1-flash", "deepseek-flash", False),
            ("https://api.deepseek.com", "deepseek-v4-pro", "deepseek-v4-pro", False),
            (
                "https://openrouter.ai/api/v1",
                "deepseek/deepseek-v4.1-flash",
                "deepseek/deepseek-v4.1-flash",
                True,
            ),
            (
                "https://gateway.example/v1",
                "deepseek/deepseek-v4.1-flash",
                "deepseek/deepseek-v4.1-flash",
                False,
            ),
        ):
            with self.subTest(url=url, model=model):
                self.config.DEEPSEEK_BASE_URL = url
                self.config.DEEPSEEK_MODEL = model
                await self.generate(DeepSeekProvider, deepseek_response())
                body = json.loads(self.requests[-1].content)
                self.assertEqual(body["model"], expected)
                if openrouter:
                    self.assertEqual(body["reasoning"], {"enabled": False})
                    self.assertNotIn("thinking", body)
                else:
                    self.assertEqual(body["thinking"], {"type": "disabled"})
                    self.assertNotIn("reasoning", body)

    async def test_missing_key_never_calls_network(self):
        for key in (None, SecretStr(""), SecretStr("  ")):
            with self.subTest(key=key):
                self.config.DEEPSEEK_API_KEY = key
                with self.assertRaisesRegex(DeepSeekError, "not configured"):
                    await self.generate(DeepSeekProvider, deepseek_response())
        self.assertEqual(self.requests, [])

    async def test_safe_http_errors(self):
        for status, message in (
            (401, "HTTP 401"),
            (402, "Add credits"),
            (429, "HTTP 429"),
            (500, "HTTP 500"),
        ):
            with self.subTest(status=status):
                with self.assertRaisesRegex(DeepSeekError, message) as caught:
                    await self.generate(
                        DeepSeekProvider, httpx.Response(status, text="private details")
                    )
                self.assertNotIn("private details", str(caught.exception))

    async def test_network_failures(self):
        for error, message in (
            (httpx.ReadTimeout("private"), "timed out"),
            (httpx.ConnectError("private"), "Could not connect"),
        ):
            with self.subTest(error=type(error).__name__):
                with self.assertRaisesRegex(DeepSeekError, message):
                    await self.generate(DeepSeekProvider, error)

    async def test_malformed_envelopes(self):
        for data in (None, {}, {"choices": []}, {"choices": [None]}, {"choices": [{}]}):
            with self.subTest(data=data):
                with self.assertRaisesRegex(DeepSeekError, "invalid response"):
                    await self.generate(
                        DeepSeekProvider, httpx.Response(200, content=json.dumps(data))
                    )
        with self.assertRaisesRegex(DeepSeekError, "invalid response"):
            await self.generate(DeepSeekProvider, httpx.Response(200, text="not JSON"))

    async def test_truncated_blocked_and_empty_output(self):
        for finish, content, message in (
            ("length", "{}", "truncated"),
            ("content_filter", "", "did not finish"),
            ("stop", " ", "empty response"),
            ("stop", None, "empty response"),
        ):
            with self.subTest(finish=finish, content=content):
                with self.assertRaisesRegex(DeepSeekError, message):
                    await self.generate(DeepSeekProvider, deepseek_response(content, finish))


class GeminiProviderTests(ProviderTestCase):
    async def test_native_request_and_split_text_without_thoughts(self):
        self.config.GEMINI_MODEL = "models/gemini-2.5-flash"
        self.config.GEMINI_MAX_TOKENS = 4096
        response = httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {"thought": True, "text": "private reasoning"},
                                {"text": CONTENT[:15]},
                                {"text": CONTENT[15:]},
                            ]
                        },
                    }
                ]
            },
        )
        self.assertEqual(await self.generate(GeminiProvider, response), CONTENT)
        request = self.requests[0]
        self.assertEqual(
            str(request.url),
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        )
        self.assertEqual(request.headers["x-goog-api-key"], "test-gemini-key")
        self.assertNotIn("test-gemini-key", str(request.url))
        body = json.loads(request.content)
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], REQUEST.system_prompt)
        self.assertEqual(body["contents"][0]["parts"][0]["text"], REQUEST.user_prompt)
        config = body["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertEqual(config["maxOutputTokens"], 4096)
        self.assertIn("title", config["responseJsonSchema"]["properties"])
        self.assertNotIn("minLength", config["responseJsonSchema"]["properties"]["title"])
        self.assertEqual(REQUEST.response_schema["properties"]["title"]["minLength"], 1)

    async def test_missing_key_never_calls_network(self):
        for key in (None, SecretStr(""), SecretStr("  ")):
            with self.subTest(key=key):
                self.config.GEMINI_API_KEY = key
                with self.assertRaisesRegex(GeminiError, "not configured"):
                    await self.generate(GeminiProvider, gemini_response())
        self.assertEqual(self.requests, [])

    async def test_safe_http_errors(self):
        for status, message in (
            (400, "HTTP 400"),
            (401, "authentication"),
            (403, "permission"),
            (404, "GEMINI_MODEL"),
            (429, "quota"),
            (500, "HTTP 500"),
        ):
            with self.subTest(status=status):
                with self.assertRaisesRegex(GeminiError, message) as caught:
                    await self.generate(
                        GeminiProvider, httpx.Response(status, text="private details")
                    )
                self.assertNotIn("private details", str(caught.exception))

    async def test_network_failures(self):
        for error, message in (
            (httpx.ReadTimeout("private"), "timed out"),
            (httpx.ConnectError("private"), "Could not connect"),
        ):
            with self.subTest(error=type(error).__name__):
                with self.assertRaisesRegex(GeminiError, message):
                    await self.generate(GeminiProvider, error)

    async def test_malformed_envelopes(self):
        for data in (
            None,
            [],
            {},
            {"candidates": []},
            {"candidates": [None]},
            {"candidates": [{"finishReason": "STOP", "content": {"parts": [None]}}]},
        ):
            with self.subTest(data=data):
                with self.assertRaisesRegex(GeminiError, "invalid response"):
                    await self.generate(
                        GeminiProvider, httpx.Response(200, content=json.dumps(data))
                    )
        with self.assertRaisesRegex(GeminiError, "invalid response"):
            await self.generate(GeminiProvider, httpx.Response(200, text="not JSON"))

    async def test_blocked_truncated_and_empty_output(self):
        with self.assertRaisesRegex(GeminiError, "blocked"):
            await self.generate(
                GeminiProvider,
                httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
            )
        for finish, content, message in (
            ("MAX_TOKENS", "{}", "truncated"),
            ("SAFETY", "", "did not finish"),
            ("STOP", " ", "empty response"),
        ):
            with self.subTest(finish=finish):
                with self.assertRaisesRegex(GeminiError, message):
                    await self.generate(GeminiProvider, gemini_response(content, finish))


class ProviderCompositionTests(unittest.TestCase):
    def test_explicit_factory_configuration(self):
        self.assertIsInstance(create_json_generator(make_settings()), DeepSeekProvider)
        self.assertIsInstance(
            create_json_generator(make_settings(STORY_PROVIDER="gemini")), GeminiProvider
        )
        with self.assertRaises(ValidationError):
            make_settings(STORY_PROVIDER="unknown")

    def test_gemini_schema_adapter_is_generic_and_does_not_mutate_input(self):
        original = json.loads(json.dumps(REQUEST.response_schema))
        simplified = simplify_gemini_schema(REQUEST.response_schema)
        self.assertEqual(REQUEST.response_schema, original)
        self.assertIn("title", simplified["properties"])
        self.assertEqual(simplified["required"], ["title", "value"])
