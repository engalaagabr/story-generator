from fastapi import FastAPI
from app.core.lifespan import lifespan
from app.api.routers.health import router as health_router
from app.api.routers.story import router as story_router

app = FastAPI(lifespan=lifespan)

app.include_router(health_router)
app.include_router(story_router)