import uuid
from datetime import datetime

from pydantic import BaseModel


class ComponentCreate(BaseModel):
    name_internal: str
    description: str | None = None
    category_id: uuid.UUID | None = None


class ComponentUpdate(BaseModel):
    name_internal: str | None = None
    name_normalized: str | None = None
    description: str | None = None
    search_queries: list[str] | None = None
    category_id: uuid.UUID | None = None
    enrichment_status: str | None = None


class ComponentRead(BaseModel):
    id: uuid.UUID
    name_internal: str
    name_normalized: str | None
    description: str | None
    search_queries: list[str]
    category_id: uuid.UUID | None
    enrichment_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
