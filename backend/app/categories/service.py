import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.categories.schemas import CategoryCreate, CategoryTree, CategoryUpdate


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    if data.parent_id:
        parent = await db.get(Category, data.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
    cat = Category(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Category:
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


async def is_leaf(db: AsyncSession, category_id: uuid.UUID) -> bool:
    result = await db.execute(select(Category).where(Category.parent_id == category_id).limit(1))
    return result.scalar_one_or_none() is None


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
    cat = await get_category(db, category_id)
    if not await is_leaf(db, category_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete category with children")
    await db.delete(cat)
    await db.commit()


async def get_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category))
    return list(result.scalars().all())


async def build_tree(db: AsyncSession) -> list[CategoryTree]:
    all_cats = await get_all_categories(db)
    leaf_set = {c.id for c in all_cats}
    for c in all_cats:
        if c.parent_id in leaf_set:
            leaf_set.discard(c.parent_id)

    cat_map: dict[uuid.UUID, CategoryTree] = {}
    for c in all_cats:
        node = CategoryTree(
            id=c.id, name=c.name, description=c.description,
            parent_id=c.parent_id, is_leaf=(c.id in leaf_set),
            created_at=c.created_at,
        )
        cat_map[c.id] = node

    roots = []
    for node in cat_map.values():
        if node.parent_id is None:
            roots.append(node)
        elif node.parent_id in cat_map:
            cat_map[node.parent_id].children.append(node)
    return roots
