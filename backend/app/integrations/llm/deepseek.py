from urllib.parse import urlsplit

import httpx

from app.core.config import Settings
from app.integrations.llm.contracts import JsonGenerationRequest
from app.integrations.llm.exceptions import DeepSeekError


class DeepSeekProvider:
    def __init__(
        self, config: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.config = config
        self.transport = transport

    @property
    def api_model(self) -> str:
        """Resolve the V4.1 Flash alias only for DeepSeek's official endpoint."""
        if urlsplit(
            self.config.DEEPSEEK_BASE_URL
        ).hostname == "api.deepseek.com" and self.config.DEEPSEEK_MODEL in {
            "deepseek/deepseek-v4.1-flash",
            "deepseek-v4.1-flash",
        }:
            return "deepseek-flash"
        return self.config.DEEPSEEK_MODEL

    async def generate_json(self, request: JsonGenerationRequest) -> str:
        api_key = self.config.DEEPSEEK_API_KEY
        if api_key is None or not api_key.get_secret_value().strip():
            raise DeepSeekError("DEEPSEEK_API_KEY is not configured.")

        reasoning_options = (
            {"reasoning": {"enabled": False}}
            if urlsplit(self.config.DEEPSEEK_BASE_URL).hostname == "openrouter.ai"
            else {"thinking": {"type": "disabled"}}
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.config.DEEPSEEK_TIMEOUT_SECONDS, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key.get_secret_value()}"},
                    json={
                        "model": self.api_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": request.system_prompt,
                            },
                            {"role": "user", "content": request.user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        **reasoning_options,
                        "max_tokens": self.config.DEEPSEEK_MAX_TOKENS,
                        "stream": False,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            raise DeepSeekError("DeepSeek request timed out. Please try again.") from None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 402:
                raise DeepSeekError(
                    "Insufficient API balance (HTTP 402). Add credits to your "
                    "configured provider account and try again."
                ) from None
            raise DeepSeekError(
                f"DeepSeek request failed (HTTP {exc.response.status_code})."
            ) from None
        except httpx.RequestError:
            raise DeepSeekError("Could not connect to DeepSeek. Please try again.") from None

        try:
            choice = response.json()["choices"][0]
            finish_reason = choice["finish_reason"]
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise DeepSeekError("DeepSeek returned an invalid response.") from None
        if finish_reason == "length":
            raise DeepSeekError("DeepSeek output was truncated. Increase DEEPSEEK_MAX_TOKENS.")
        if finish_reason != "stop":
            raise DeepSeekError("DeepSeek did not finish generating the response.")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek returned an empty response. Please try again.")
        return content
