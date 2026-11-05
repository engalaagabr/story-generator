"""Select a configured adapter at the composition boundary."""

from app.core.config import Settings
from app.integrations.llm.contracts import JsonGenerator
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.llm.gemini import GeminiProvider


def create_json_generator(config: Settings) -> JsonGenerator:
    if config.STORY_PROVIDER == "gemini":
        return GeminiProvider(config)
    if config.STORY_PROVIDER == "deepseek":
        return DeepSeekProvider(config)
    raise ValueError("Unsupported STORY_PROVIDER. Choose deepseek or gemini.")
