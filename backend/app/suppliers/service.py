import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.categories.models import Category
from app.suppliers.models import Supplier, SupplierCategory
from app.suppliers.schemas import CoverageItem, SupplierCreate


async def create_supplier(db: AsyncSession, data: SupplierCreate) -> Supplier:
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def get_suppliers(db: AsyncSession) -> list[Supplier]:
    result = await db.execute(select(Supplier).options(selectinload(Supplier.category_links)))
    return list(result.scalars().all())


async def assign_category(db: AsyncSession, supplier_id: uuid.UUID, category_id: uuid.UUID) -> None:
    link = SupplierCategory(supplier_id=supplier_id, category_id=category_id)
    db.add(link)
    await db.commit()


async def get_coverage(db: AsyncSession) -> list[CoverageItem]:
    count_q = (
        select(SupplierCategory.category_id, func.count(SupplierCategory.supplier_id).label("cnt"))
        .group_by(SupplierCategory.category_id)
        .subquery()
    )
    result = await db.execute(
        select(Category.id, Category.name, count_q.c.cnt)
        .outerjoin(count_q, Category.id == count_q.c.category_id)
    )
    items = []
    for row in result.all():
        cnt = row.cnt or 0
        if cnt < 2:
            status = "red"
        elif cnt < 4:
            status = "yellow"
        else:
            status = "green"
        items.append(CoverageItem(category_id=row.id, category_name=row.name, supplier_count=cnt, status=status))
    return items
