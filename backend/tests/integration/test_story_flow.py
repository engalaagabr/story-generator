import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_db
from app.core.exceptions import StoryGenerationError
from app.db.registry import Base
from app.db.session import Database
from app.integrations.llm.contracts import JsonGenerator
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.llm.gemini import GeminiProvider
from app.main import create_app
from app.modules.jobs.models import StoryJob
from app.modules.jobs.processor import logger
from app.modules.jobs.repository import StoryJobRepository
from app.modules.jobs.service import StoryJobService
from app.modules.stories.generation import StoryGenerationService
from app.modules.stories.models import Story, StoryNode
from app.modules.stories.repository import StoryRepository
from tests.support import FIXTURE, make_settings, story_payload


class StoryFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        url = f"sqlite+aiosqlite:///{Path(self.directory.name) / 'test.sqlite'}"
        self.database = Database(url)
        self.sessions = self.database.session_factory
        async with self.database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.config = make_settings(DATABASE_URL=url)
        self.provider = AsyncMock(spec=JsonGenerator)
        self.provider.generate_json.return_value = FIXTURE.read_text()
        self.generator = StoryGenerationService(self.provider)
        self.app = create_app(self.config, database=self.database, generator=self.generator)
        self.processor = self.app.state.job_processor
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.database.close()

    async def create(self):
        response = await self.client.post("/api/story/create", json={"theme": "Space"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        return response.json()

    async def get_job(self, job_id):
        response = await self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def assert_no_stories(self):
        async with self.sessions() as session:
            for model in (Story, StoryNode):
                count = await session.scalar(select(func.count()).select_from(model))
                self.assertEqual(count, 0)

    async def test_create_poll_read_and_remap_every_choice(self):
        self.client.cookies.set("session_id", "existing-session")
        created = await self.create()
        self.provider.generate_json.assert_awaited_once()
        self.assertEqual(
            self.provider.generate_json.call_args.args[0].user_prompt, "Story theme: Space"
        )
        job = await self.get_job(created["job_id"])
        self.assertEqual(job["status"], "completed")
        self.assertIsNotNone(job["completed_at"])
        self.assertIsNone(job["error"])
        response = await self.client.get(f"/api/story/{job['story_id']}/complete")
        self.assertEqual(response.status_code, 200)
        story = response.json()
        self.assertEqual(story["session_id"], "existing-session")
        self.assertEqual(len(story["all_nodes"]), 5)
        self.assertNotEqual(story["root_node"]["id"], 10)
        actual_by_content = {node["content"]: node for node in story["all_nodes"].values()}
        expected_by_id = {node["id"]: node for node in story_payload()["nodes"]}
        for expected in expected_by_id.values():
            actual = actual_by_content[expected["content"]]
            for option, expected_option in zip(actual["options"], expected["options"], strict=True):
                target = story["all_nodes"][str(option["node_id"])]
                self.assertEqual(
                    target["content"], expected_by_id[expected_option["node_id"]]["content"]
                )
                self.assertEqual(option["text"], expected_option["text"])
        async with self.sessions() as session:
            other = Story(title="Unrelated", session_id="other")
            session.add(other)
            await session.flush()
            session.add(StoryNode(story_id=other.id, content="Other", is_root=True))
            await session.commit()
        response = await self.client.get(f"/api/story/{job['story_id']}/complete")
        self.assertEqual(len(response.json()["all_nodes"]), 5)

    async def test_sets_session_cookie_for_new_visitors(self):
        await self.create()
        self.assertTrue(self.client.cookies.get("session_id"))

    async def test_real_provider_adapters_integrate_with_services_and_database(self):
        for provider_type in (DeepSeekProvider, GeminiProvider):
            with self.subTest(provider=provider_type.__name__):

                def handler(request):
                    content = FIXTURE.read_text()
                    if provider_type is DeepSeekProvider:
                        return httpx.Response(
                            200,
                            json={
                                "choices": [
                                    {"finish_reason": "stop", "message": {"content": content}}
                                ]
                            },
                        )
                    return httpx.Response(
                        200,
                        json={
                            "candidates": [
                                {"finishReason": "STOP", "content": {"parts": [{"text": content}]}}
                            ]
                        },
                    )

                provider = provider_type(self.config, transport=httpx.MockTransport(handler))
                app = create_app(
                    self.config, database=self.database, generator=StoryGenerationService(provider)
                )
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/story/create", json={"theme": "Space"})
                    job = (await client.get(f"/api/jobs/{response.json()['job_id']}")).json()
                    self.assertEqual(job["status"], "completed", job["error"])

    async def test_invalid_generated_output_fails_without_database_writes(self):
        self.provider.generate_json.return_value = "{}"
        with self.assertLogs(logger, level="ERROR"):
            created = await self.create()
        job = await self.get_job(created["job_id"])
        self.assertEqual(job["status"], "failed")
        self.assertIn("required structure", job["error"])
        self.assertIsNone(job["story_id"])
        self.assertIsNotNone(job["completed_at"])
        await self.assert_no_stories()

    async def test_safe_failures_are_exposed_but_unknown_errors_are_sanitized(self):
        for error, expected in (
            (
                StoryGenerationError("Configured model quota exceeded."),
                "Configured model quota exceeded.",
            ),
            (
                RuntimeError("private credentials and connection details"),
                "Story generation failed. Please try again.",
            ),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(self.generator, "generate", side_effect=error):
                    with self.assertLogs(logger, level="ERROR"):
                        created = await self.create()
                job = await self.get_job(created["job_id"])
                self.assertEqual(job["status"], "failed")
                self.assertEqual(job["error"], expected)
                await self.assert_no_stories()

    async def test_database_flush_failure_rolls_back_all_partial_writes(self):
        async def invalid_story(repository, generated, session_id):
            story = Story(title=None, session_id=session_id)
            repository.session.add(story)
            await repository.session.flush()
            return story

        with patch.object(StoryRepository, "create_generated", new=invalid_story):
            with self.assertLogs(logger, level="ERROR"):
                created = await self.create()
        job = await self.get_job(created["job_id"])
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["story_id"])
        self.assertNotIn("INSERT", job["error"])
        await self.assert_no_stories()

    async def test_failure_after_story_flush_rolls_back_story_and_nodes(self):
        original = StoryRepository.create_generated

        async def fail_after_write(repository, generated, session_id):
            await original(repository, generated, session_id)
            await repository.session.flush()
            raise RuntimeError("private post-write failure")

        with patch.object(StoryRepository, "create_generated", new=fail_after_write):
            with self.assertLogs(logger, level="ERROR"):
                created = await self.create()
        self.assertEqual((await self.get_job(created["job_id"]))["status"], "failed")
        await self.assert_no_stories()

    async def test_atomic_claim_prevents_duplicate_generation(self):
        async with self.sessions() as session:
            job = await StoryJobService(StoryJobRepository(session)).create("session", "Space")
            job_id = job.job_id
        entered, release = asyncio.Event(), asyncio.Event()

        async def generate(request):
            entered.set()
            await release.wait()
            return FIXTURE.read_text()

        self.provider.generate_json.side_effect = generate
        first = asyncio.create_task(self.processor.process(job_id))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            await asyncio.wait_for(self.processor.process(job_id), timeout=5)
            self.provider.generate_json.assert_awaited_once()
        finally:
            release.set()
            await first
        self.assertEqual((await self.get_job(job_id))["status"], "completed")

    async def test_processor_skips_missing_and_finished_jobs(self):
        created = await self.create()
        self.provider.generate_json.reset_mock()
        await self.processor.process(created["job_id"])
        await self.processor.process("does-not-exist")
        self.provider.generate_json.assert_not_called()

    async def test_invalid_input_does_not_create_a_job(self):
        response = await self.client.post("/api/story/create", json={})
        self.assertEqual(response.status_code, 422)
        self.provider.generate_json.assert_not_called()
        async with self.sessions() as session:
            count = await session.scalar(select(func.count()).select_from(StoryJob))
            self.assertEqual(count, 0)

    async def test_unknown_resources_and_invalid_ids(self):
        for path, detail in (
            ("/api/jobs/missing", "Job not found"),
            ("/api/story/999/complete", "Story not found"),
        ):
            response = await self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": detail})
        response = await self.client.get("/api/story/not-an-integer/complete")
        self.assertEqual(response.status_code, 422)

    async def test_story_without_root_returns_expected_error(self):
        async with self.sessions() as session:
            story = Story(title="Incomplete", session_id="session")
            session.add(story)
            await session.commit()
            story_id = story.id
        response = await self.client.get(f"/api/story/{story_id}/complete")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Story root node not found"})

    async def test_health_and_database_failure(self):
        response = await self.client.get("/api/health")
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

        async def unavailable_db():
            session = AsyncMock()
            session.execute.side_effect = SQLAlchemyError("private connection details")
            yield session

        self.app.dependency_overrides[get_db] = unavailable_db
        response = await self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy", "database": "unavailable"})

    async def test_app_lifespan_closes_its_database(self):
        with patch.object(self.database, "close", new_callable=AsyncMock) as close:
            async with self.app.router.lifespan_context(self.app):
                close.assert_not_awaited()
            close.assert_awaited_once()

    async def test_app_instances_do_not_share_injected_resources(self):
        other_provider = AsyncMock(spec=JsonGenerator)
        other = create_app(
            self.config, database=self.database, generator=StoryGenerationService(other_provider)
        )
        self.assertIsNot(other.state.job_processor, self.processor)
        self.assertIs(other.state.job_processor.generator.provider, other_provider)
        self.assertIs(self.processor.generator.provider, self.provider)

    async def test_public_routes_and_docs_are_unchanged(self):
        self.assertEqual(
            set(self.app.openapi()["paths"]),
            {
                "/api/health",
                "/api/story/create",
                "/api/story/{story_id}/complete",
                "/api/jobs/{job_id}",
            },
        )
        self.assertEqual((await self.client.get("/api/docs")).status_code, 200)
