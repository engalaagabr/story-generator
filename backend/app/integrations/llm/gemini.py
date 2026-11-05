from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.integrations.llm.contracts import JsonGenerationRequest
from app.integrations.llm.exceptions import GeminiError
from app.integrations.llm.json_schema import simplify_gemini_schema


class GeminiProvider:
    def __init__(
        self, config: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.config = config
        self.transport = transport

    async def generate_json(self, request: JsonGenerationRequest) -> str:
        api_key = self.config.GEMINI_API_KEY
        if api_key is None or not api_key.get_secret_value().strip():
            raise GeminiError("GEMINI_API_KEY is not configured.")

        model = quote(self.config.GEMINI_MODEL.removeprefix("models/"), safe="")
        try:
            async with httpx.AsyncClient(
                timeout=self.config.GEMINI_TIMEOUT_SECONDS, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.config.GEMINI_BASE_URL.rstrip('/')}/models/{model}:generateContent",
                    headers={"x-goog-api-key": api_key.get_secret_value()},
                    json={
                        "systemInstruction": {"parts": [{"text": request.system_prompt}]},
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": request.user_prompt}],
                            }
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "responseJsonSchema": simplify_gemini_schema(request.response_schema),
                            "maxOutputTokens": self.config.GEMINI_MAX_TOKENS,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            raise GeminiError("Gemini request timed out. Please try again.") from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise GeminiError(
                    f"Gemini authentication or permission failed (HTTP {status}). "
                    "Check GEMINI_API_KEY and its project permissions."
                ) from None
            if status == 429:
                raise GeminiError(
                    "Gemini quota or rate limit exceeded (HTTP 429). "
                    "Check your project's quota and billing, or try again later."
                ) from None
            if status == 404:
                raise GeminiError(
                    "Gemini model or endpoint not found (HTTP 404). "
                    "Check GEMINI_MODEL and GEMINI_BASE_URL."
                ) from None
            raise GeminiError(f"Gemini request failed (HTTP {status}).") from None
        except httpx.RequestError:
            raise GeminiError("Could not connect to Gemini. Please try again.") from None

        try:
            payload = response.json()
            if payload.get("promptFeedback", {}).get("blockReason"):
                raise GeminiError("Gemini blocked the request. Try a different prompt.")
            candidate = payload["candidates"][0]
            finish_reason = candidate["finishReason"]
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise GeminiError("Gemini returned an invalid response.") from None
        if finish_reason == "MAX_TOKENS":
            raise GeminiError("Gemini output was truncated. Increase GEMINI_MAX_TOKENS.")
        if finish_reason != "STOP":
            raise GeminiError(
                "Gemini did not finish generating the response. Try a different prompt."
            )
        try:
            parts = candidate["content"]["parts"]
            if not isinstance(parts, list) or any(not isinstance(part, dict) for part in parts):
                raise TypeError
            content = "".join(
                part["text"]
                for part in parts
                if not part.get("thought") and isinstance(part.get("text"), str)
            )
        except (KeyError, TypeError):
            raise GeminiError("Gemini returned an invalid response.") from None
        if not content.strip():
            raise GeminiError("Gemini returned an empty response. Please try again.")
        return content
