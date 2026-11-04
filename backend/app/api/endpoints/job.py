from fastapi import APIRouter, Depends, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job import StoryJobResponse
from backend.app.core.database import get_db
from backend.app.models.job import StoryJob

router = APIRouter()

@router.get("/{job_id}", response_model=StoryJobResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    
    job = await db.scalar(select(StoryJob).where(StoryJob.job_id == job_id))
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job  