import uuid
from datetime import datetime

from pydantic import BaseModel


class SupplierCreate(BaseModel):
    name: str
    type: str  # company | marketplace
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    notes: str | None = None


class SupplierRead(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    email: str | None
    website: str | None
    phone: str | None
    notes: str | None
    category_ids: list[uuid.UUID] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignCategoryRequest(BaseModel):
    category_id: uuid.UUID


class CoverageItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    supplier_count: int
    status: str  # red | yellow | green
