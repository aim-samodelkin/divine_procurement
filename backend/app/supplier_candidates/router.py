import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.supplier_candidates.schemas import SupplierCandidateRead
from app.supplier_candidates import service

router = APIRouter(
    prefix="/supplier-candidates",
    tags=["supplier-candidates"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SupplierCandidateRead])
async def list_candidates(
    status: str | None = Query("pending"),
    component_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_candidates(db, status=status, component_id=component_id)
    return [SupplierCandidateRead.model_validate(r) for r in rows]


@router.post("/{candidate_id}/approve")
async def approve_candidate(candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        supplier_id = await service.approve_candidate(db, candidate_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
    return {"supplier_id": str(supplier_id)}


@router.post("/{candidate_id}/reject")
async def reject_candidate(candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        await service.reject_candidate(db, candidate_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
    return {"ok": True}
