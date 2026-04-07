import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.components import service
from app.components.schemas import ComponentCreate, ComponentRead, ComponentUpdate, ImportResult
from app.database import get_db

router = APIRouter(prefix="/components", tags=["components"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ComponentRead])
async def list_components(category_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    return await service.list_components(db, category_id)


@router.post("", response_model=ComponentRead, status_code=status.HTTP_201_CREATED)
async def create_component(body: ComponentCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_component(db, body)


@router.patch("/{component_id}", response_model=ComponentRead)
async def update_component(component_id: uuid.UUID, body: ComponentUpdate, db: AsyncSession = Depends(get_db)):
    comp = await service.get_component(db, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(comp, k, v)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.post("/import", response_model=ImportResult)
async def import_components(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    return await service.import_from_csv(db, content)
