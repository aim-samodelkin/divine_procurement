import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.supplier_candidates.models import SupplierCandidate
from app.supplier_candidates.schemas import PublicSupplierRegistration
from app.suppliers import service as supplier_service
from app.suppliers.schemas import SupplierCreate


def _completeness(email: str | None, phone: str | None) -> str:
    return "complete" if (email or phone) else "incomplete"


async def list_candidates(
    db: AsyncSession, *, status: str | None = "pending", component_id: uuid.UUID | None = None
) -> list[SupplierCandidate]:
    q = select(SupplierCandidate)
    if status:
        q = q.where(SupplierCandidate.status == status)
    if component_id:
        q = q.where(SupplierCandidate.component_id == component_id)
    q = q.order_by(SupplierCandidate.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_from_registration(db: AsyncSession, body: PublicSupplierRegistration) -> SupplierCandidate:
    c = SupplierCandidate(
        name=body.name,
        type=body.type,
        email=body.email,
        website=body.website,
        phone=body.phone,
        notes=body.notes,
        category_ids=list(body.category_ids),
        completeness=_completeness(body.email, body.phone),
        status="pending",
        source="registration",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def insert_agent_candidates(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    component_id: uuid.UUID,
    category_ids: list[uuid.UUID],
    rows: list[dict],
) -> int:
    n = 0
    for row in rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        email = row.get("email")
        phone = row.get("phone")
        row_type = row.get("type") or "company"
        if row_type not in ("company", "marketplace"):
            row_type = "company"
        c = SupplierCandidate(
            job_id=job_id,
            component_id=component_id,
            category_ids=list(category_ids),
            name=name,
            type=row_type,
            email=email,
            website=row.get("website"),
            phone=phone,
            notes=row.get("notes"),
            completeness=_completeness(email, phone),
            status="pending",
            source="agent",
        )
        db.add(c)
        n += 1
    await db.commit()
    return n


async def approve_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> uuid.UUID:
    c = await db.get(SupplierCandidate, candidate_id)
    if not c:
        raise ValueError("candidate not found")
    if c.status != "pending":
        raise ValueError("candidate not pending")
    sup = await supplier_service.create_supplier(
        db,
        SupplierCreate(
            name=c.name,
            type=c.type,
            email=c.email,
            website=c.website,
            phone=c.phone,
            notes=c.notes,
        ),
    )
    seen: set[uuid.UUID] = set()
    for cat_id in c.category_ids:
        if cat_id in seen:
            continue
        seen.add(cat_id)
        await supplier_service.assign_category(db, sup.id, cat_id)
    c.status = "approved"
    await db.commit()
    return sup.id


async def reject_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> None:
    c = await db.get(SupplierCandidate, candidate_id)
    if not c:
        raise ValueError("candidate not found")
    c.status = "rejected"
    await db.commit()
