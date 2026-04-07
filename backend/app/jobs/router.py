import uuid

import arq
import arq.connections
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.jobs.schemas import EnqueueResponse, JobRead
from app.jobs.service import create_job, get_job

router = APIRouter(tags=["jobs"], dependencies=[Depends(get_current_user)])


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/components/{component_id}/enrich", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_enrichment(component_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job_record = await create_job(db, type="enrich_component", payload={"component_id": str(component_id)})
    pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("enrich_component_task", component_id=str(component_id), job_id=str(job_record.id))
    await pool.aclose()
    return EnqueueResponse(job_id=job_record.id)


@router.post("/components/{component_id}/discover-suppliers", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_discover_suppliers(component_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job_record = await create_job(db, type="discover_suppliers", payload={"component_id": str(component_id)})
    pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job(
        "discover_suppliers_task",
        component_id=str(component_id),
        job_id=str(job_record.id),
    )
    await pool.aclose()
    return EnqueueResponse(job_id=job_record.id)
