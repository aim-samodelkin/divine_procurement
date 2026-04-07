import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SupplierCandidateRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None
    component_id: uuid.UUID | None
    category_ids: list[uuid.UUID]
    name: str
    type: str
    email: str | None
    website: str | None
    phone: str | None
    notes: str | None
    completeness: str
    status: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicSupplierRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(default="company", pattern="^(company|marketplace)$")
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    notes: str | None = None
    category_ids: list[uuid.UUID] = Field(default_factory=list)
