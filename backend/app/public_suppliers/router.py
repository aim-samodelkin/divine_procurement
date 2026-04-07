from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.supplier_candidates.schemas import PublicSupplierRegistration, SupplierCandidateRead
from app.supplier_candidates.service import create_from_registration

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/supplier-registration", response_model=SupplierCandidateRead, status_code=status.HTTP_201_CREATED)
async def public_register(
    body: PublicSupplierRegistration,
    db: AsyncSession = Depends(get_db),
    x_registration_token: str | None = Header(None, alias="X-Registration-Token"),
):
    if not settings.public_supplier_registration_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registration not configured")
    if not x_registration_token or x_registration_token != settings.public_supplier_registration_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid registration token")
    c = await create_from_registration(db, body)
    return SupplierCandidateRead.model_validate(c)
