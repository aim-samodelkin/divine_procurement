import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.categories import service
from app.categories.schemas import CategoryCreate, CategoryRead, CategoryTree, CategoryUpdate
from app.database import get_db

router = APIRouter(prefix="/categories", tags=["categories"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    cat = await service.create_category(db, body)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.get("/tree", response_model=list[CategoryTree])
async def get_tree(db: AsyncSession = Depends(get_db)):
    return await service.build_tree(db)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category(db, category_id)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(category_id: uuid.UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category(db, category_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await service.delete_category(db, category_id)
