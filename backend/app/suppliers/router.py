import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.suppliers import service
from app.suppliers.schemas import AssignCategoryRequest, CoverageItem, SupplierCreate, SupplierRead

router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(get_current_user)])


@router.get("/coverage", response_model=list[CoverageItem])
async def get_coverage(db: AsyncSession = Depends(get_db)):
    return await service.get_coverage(db)


@router.get("", response_model=list[SupplierRead])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    suppliers = await service.get_suppliers(db)
    result = []
    for s in suppliers:
        result.append(SupplierRead(
            id=s.id, name=s.name, type=s.type, email=s.email, website=s.website,
            phone=s.phone, notes=s.notes, created_at=s.created_at,
            category_ids=[lnk.category_id for lnk in s.category_links],
        ))
    return result


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db)):
    s = await service.create_supplier(db, body)
    return SupplierRead(
        id=s.id, name=s.name, type=s.type, email=s.email, website=s.website,
        phone=s.phone, notes=s.notes, created_at=s.created_at, category_ids=[],
    )


@router.post("/{supplier_id}/categories")
async def assign_category(supplier_id: uuid.UUID, body: AssignCategoryRequest, db: AsyncSession = Depends(get_db)):
    await service.assign_category(db, supplier_id, body.category_id)
    return {"ok": True}
