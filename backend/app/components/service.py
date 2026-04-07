import csv
import io
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models import Component
from app.components.schemas import ComponentCreate, ImportResult


async def create_component(db: AsyncSession, data: ComponentCreate) -> Component:
    comp = Component(**data.model_dump())
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp


async def list_components(db: AsyncSession, category_id: uuid.UUID | None = None) -> list[Component]:
    q = select(Component)
    if category_id:
        q = q.where(Component.category_id == category_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_component(db: AsyncSession, component_id: uuid.UUID) -> Component | None:
    return await db.get(Component, component_id)


async def import_from_csv(db: AsyncSession, content: bytes) -> ImportResult:
    from sqlalchemy.exc import IntegrityError

    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    imported, skipped, errors = 0, 0, []

    for i, row in enumerate(reader, start=2):
        name = (row.get("name_internal") or "").strip()
        cat_str = (row.get("category_id") or "").strip()
        if not name:
            skipped += 1
            errors.append(f"Row {i}: missing name_internal")
            continue
        cat_id = None
        if cat_str:
            try:
                cat_id = uuid.UUID(cat_str)
            except ValueError:
                skipped += 1
                errors.append(f"Row {i}: invalid category_id '{cat_str}'")
                continue
        try:
            async with db.begin_nested():
                db.add(Component(name_internal=name, category_id=cat_id))
            imported += 1
        except IntegrityError as e:
            skipped += 1
            errors.append(f"Row {i}: integrity error — {e.orig}")

    await db.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=errors)
