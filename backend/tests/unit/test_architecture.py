"""Executable dependency rules keep the documented boundaries from drifting."""

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


class ArchitectureTests(unittest.TestCase):
    def test_external_adapters_do_not_import_business_features_or_database(self):
        for path in (APP / "integrations").rglob("*.py"):
            for name in imports(path):
                with self.subTest(path=path.name, dependency=name):
                    self.assertFalse(name.startswith(("app.modules", "app.api", "app.db")))

    def test_features_do_not_import_http_entrypoint_or_concrete_model_providers(self):
        for path in (APP / "modules").rglob("*.py"):
            for name in imports(path):
                with self.subTest(path=str(path.relative_to(APP)), dependency=name):
                    self.assertFalse(name.startswith(("fastapi", "app.api", "app.main")))
                    self.assertNotIn(
                        name,
                        {
                            "app.integrations.llm.deepseek",
                            "app.integrations.llm.gemini",
                            "app.integrations.llm.factory",
                        },
                    )

    def test_http_routes_do_not_issue_queries_or_construct_repositories(self):
        for path in (APP / "api/routes").glob("*.py"):
            for name in imports(path):
                self.assertFalse(name.endswith(".repository"), path.name)
                self.assertFalse(name.startswith("sqlalchemy"), path.name)

    def test_model_and_schema_imports_need_no_database_configuration(self):
        code = """
import os
import sqlalchemy.ext.asyncio as sa
def forbidden(*args, **kwargs):
    raise AssertionError('Database engine created during domain import')
sa.create_async_engine = forbidden
from app.db.registry import Base
from app.modules.stories.generation import StoryGenerationService
from app.integrations.llm.factory import create_json_generator
assert set(Base.metadata.tables) == {'stories', 'story_nodes', 'story_jobs'}
"""
        env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
