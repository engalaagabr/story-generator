"""Composition root: construct resources, connect features, expose the ASGI app."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db.session import Database
from app.integrations.llm.factory import create_json_generator
from app.modules.jobs.processor import StoryJobProcessor
from app.modules.stories.generation import StoryGenerationService


def create_app(
    config: Settings | None = None,
    *,
    database: Database | None = None,
    generator: StoryGenerationService | None = None,
) -> FastAPI:
    config = config if config is not None else get_settings()
    database = database if database is not None else Database(config.DATABASE_URL)
    generator = (
        generator
        if generator is not None
        else StoryGenerationService(create_json_generator(config))
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        lifespan=lifespan,
        docs_url="/api/docs",
        title="Story Generator API",
        version="0.1.0",
    )
    app.state.database = database
    app.state.job_processor = StoryJobProcessor(database.session_factory, generator)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
