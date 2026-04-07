import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobRead(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class EnqueueResponse(BaseModel):
    job_id: uuid.UUID
