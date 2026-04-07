import pytest


@pytest.mark.asyncio
async def test_create_supplier(auth_client):
    resp = await auth_client.post("/suppliers", json={
        "name": "ООО Поставщик", "type": "company", "email": "s@example.com"
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "company"


@pytest.mark.asyncio
async def test_create_marketplace_supplier(auth_client):
    resp = await auth_client.post("/suppliers", json={
        "name": "ChipDip", "type": "marketplace", "website": "https://chipdip.ru"
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "marketplace"


@pytest.mark.asyncio
async def test_assign_category(auth_client, db):
    from app.categories.schemas import CategoryCreate
    from app.categories.service import create_category
    cat = await create_category(db, CategoryCreate(name="Electronics"))
    supplier = await auth_client.post("/suppliers", json={"name": "S", "type": "company"})
    sid = supplier.json()["id"]
    resp = await auth_client.post(f"/suppliers/{sid}/categories", json={"category_id": str(cat.id)})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_coverage_returns_categories(auth_client, db):
    resp = await auth_client.get("/suppliers/coverage")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
