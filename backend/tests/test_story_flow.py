import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import create_app
from app.models.job import StoryJob
from app.models.story import Story, StoryNode
from app.services.job_service import create_story_job
from app.workers import story_tasks


class StoryFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database_path = Path(self.directory.name) / "test.sqlite"
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.app = create_app()

        async def test_db():
            async with self.sessions() as db:
                yield db

        self.app.dependency_overrides[get_db] = test_db
        worker_sessions = patch.object(story_tasks, "SessionLocal", self.sessions)
        worker_sessions.start()
        self.addCleanup(worker_sessions.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def generate_story(self, db, session_id, theme):
        story = Story(title=theme, session_id=session_id)
        db.add(story)
        await db.flush()
        ending = StoryNode(
            story_id=story.id,
            content="You made it home.",
            is_ending=True,
            is_winning_ending=True,
            options=[],
        )
        db.add(ending)
        await db.flush()
        db.add(
            StoryNode(
                story_id=story.id,
                content="Choose a path.",
                is_root=True,
                options=[{"text": "Go home", "node_id": ending.id}],
            )
        )
        return story

    async def test_create_poll_and_read_complete_story(self):
        self.client.cookies.set("session_id", "existing-session")
        with patch.object(
            story_tasks.StoryGenerator, "generate_story", side_effect=self.generate_story
        ) as generate:
            response = await self.client.post("/api/story/create", json={"theme": "Space"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        generate.assert_awaited_once()
        self.assertEqual(generate.call_args.args[1:], ("existing-session", "Space"))

        job_response = await self.client.get(f"/api/jobs/{response.json()['job_id']}")
        self.assertEqual(job_response.status_code, 200)
        job = job_response.json()
        self.assertEqual(job["status"], "completed")
        self.assertIsNotNone(job["completed_at"])
        self.assertIsNone(job["error"])

        result = await self.client.get(f"/api/story/{job['story_id']}/complete")
        self.assertEqual(result.status_code, 200)
        story = result.json()
        self.assertEqual(story["title"], "Space")
        self.assertEqual(story["session_id"], "existing-session")
        self.assertEqual(len(story["all_nodes"]), 2)
        self.assertEqual(story["root_node"]["content"], "Choose a path.")
        ending_id = str(story["root_node"]["options"][0]["node_id"])
        self.assertTrue(story["all_nodes"][ending_id]["is_winning_ending"])

        async with self.sessions() as db:
            other = Story(title="Unrelated", session_id="other-session")
            db.add(other)
            await db.flush()
            db.add(StoryNode(story_id=other.id, content="Other", is_root=True))
            await db.commit()
        result = await self.client.get(f"/api/story/{job['story_id']}/complete")
        self.assertEqual(len(result.json()["all_nodes"]), 2)

    async def test_placeholder_records_failure_and_sets_session_cookie(self):
        with self.assertLogs(story_tasks.logger, level="ERROR"):
            response = await self.client.post("/api/story/create", json={"theme": "Space"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies.get("session_id"))
        result = await self.client.get(f"/api/jobs/{response.json()['job_id']}")
        self.assertEqual(result.json()["status"], "failed")
        self.assertEqual(result.json()["error"], "Story generation is not implemented yet.")
        self.assertIsNotNone(result.json()["completed_at"])
        self.assertIsNone(result.json()["story_id"])

    async def test_generation_failure_rolls_back_partial_story(self):
        async def fail_after_write(db, session_id, theme):
            db.add(Story(title=theme, session_id=session_id))
            await db.flush()
            raise RuntimeError("Generation failed")

        with (
            patch.object(
                story_tasks.StoryGenerator, "generate_story", side_effect=fail_after_write
            ),
            self.assertLogs(story_tasks.logger, level="ERROR"),
        ):
            response = await self.client.post("/api/story/create", json={"theme": "Space"})
        result = await self.client.get(f"/api/jobs/{response.json()['job_id']}")
        self.assertEqual(result.json()["status"], "failed")
        self.assertEqual(result.json()["error"], "Generation failed")
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Story)), 0)

    async def test_database_flush_failure_still_records_failed_job(self):
        async def invalid_story(db, session_id, theme):
            story = Story(title=None, session_id=session_id)
            db.add(story)
            return story

        with (
            patch.object(story_tasks.StoryGenerator, "generate_story", side_effect=invalid_story),
            self.assertLogs(story_tasks.logger, level="ERROR"),
        ):
            response = await self.client.post("/api/story/create", json={"theme": "Space"})
        result = await self.client.get(f"/api/jobs/{response.json()['job_id']}")
        self.assertEqual(result.json()["status"], "failed")
        self.assertIsNotNone(result.json()["completed_at"])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Story)), 0)

    async def test_unknown_resources_return_404(self):
        for path, detail in (
            ("/api/jobs/missing", "Job not found"),
            ("/api/story/999/complete", "Story not found"),
        ):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": detail})

    async def test_story_without_root_returns_500(self):
        async with self.sessions() as db:
            story = Story(title="Incomplete", session_id="existing-session")
            db.add(story)
            await db.commit()
            story_id = story.id
        response = await self.client.get(f"/api/story/{story_id}/complete")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Story root node not found"})

    async def test_invalid_story_id_returns_422(self):
        response = await self.client.get("/api/story/not-an-integer/complete")
        self.assertEqual(response.status_code, 422)

    async def test_invalid_create_does_not_schedule_or_persist_a_job(self):
        with patch.object(story_tasks.StoryGenerator, "generate_story") as generate:
            response = await self.client.post("/api/story/create", json={})
        self.assertEqual(response.status_code, 422)
        generate.assert_not_called()
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(StoryJob)), 0)

    async def test_worker_skips_missing_and_finished_jobs(self):
        async with self.sessions() as db:
            job = await create_story_job(db, "session", "Space")
            job.status = "completed"
            await db.commit()
            job_id = job.job_id
        with patch.object(story_tasks.StoryGenerator, "generate_story") as generate:
            await story_tasks.generate_story_task("missing")
            await story_tasks.generate_story_task(job_id)
        generate.assert_not_called()

    async def test_health_success_and_database_failure(self):
        response = await self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

        async def unavailable_db():
            db = AsyncMock()
            db.execute.side_effect = SQLAlchemyError("private connection details")
            yield db

        self.app.dependency_overrides[get_db] = unavailable_db
        response = await self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy", "database": "unavailable"})

    async def test_openapi_has_only_the_expected_routes(self):
        self.assertEqual(
            set(self.app.openapi()["paths"]),
            {
                "/api/health",
                "/api/story/create",
                "/api/story/{story_id}/complete",
                "/api/jobs/{job_id}",
            },
        )
        response = await self.client.get("/api/docs")
        self.assertEqual(response.status_code, 200)



if __name__ == "__main__":
    unittest.main()
