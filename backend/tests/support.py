import json
from pathlib import Path

from app.core.config import Settings

FIXTURE = Path(__file__).parent / "fixtures" / "branching_story.json"


def story_payload() -> dict:
    return json.loads(FIXTURE.read_text())


def make_settings(**overrides) -> Settings:
    values = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "STORY_PROVIDER": "deepseek",
        "DEEPSEEK_API_KEY": "test-deepseek-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "DEEPSEEK_TIMEOUT_SECONDS": 30,
        "GEMINI_TIMEOUT_SECONDS": 30,
    }
    return Settings(_env_file=None, **(values | overrides))
