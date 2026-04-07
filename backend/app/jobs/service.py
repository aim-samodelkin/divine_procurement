import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job


async def create_job(db: AsyncSession, type: str, payload: dict[str, Any]) -> Job:
    job = Job(type=type, payload=payload)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await db.get(Job, job_id)


async def update_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    job = await db.get(Job, job_id)
    if job:
        job.status = status
        job.result = result
        job.error = error
        if status in ("done", "failed"):
            job.completed_at = datetime.now(timezone.utc)
        await db.commit()
