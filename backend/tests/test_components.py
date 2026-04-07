import io
import pytest


@pytest.mark.asyncio
async def test_create_component(auth_client, db):
    from app.categories.service import create_category
    from app.categories.schemas import CategoryCreate
    cat = await create_category(db, CategoryCreate(name="TestCat"))
    resp = await auth_client.post("/components", json={"name_internal": "Конд. 100мкФ", "category_id": str(cat.id)})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name_internal"] == "Конд. 100мкФ"
    assert data["enrichment_status"] == "pending"


@pytest.mark.asyncio
async def test_list_components(auth_client):
    resp = await auth_client.get("/components")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_csv_import(auth_client, db):
    from app.categories.service import create_category
    from app.categories.schemas import CategoryCreate
    cat = await create_category(db, CategoryCreate(name="CSVCat"))
    csv_content = f"name_internal,category_id\nКомпонент A,{cat.id}\nКомпонент B,{cat.id}\n"
    files = {"file": ("components.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await auth_client.post("/components/import", files=files)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 2


@pytest.mark.asyncio
async def test_csv_import_invalid_rows_skipped(auth_client):
    csv_content = "name_internal,category_id\n,invalid-uuid\nValid Name,00000000-0000-0000-0000-000000000000\n"
    files = {"file": ("components.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await auth_client.post("/components/import", files=files)
    assert resp.status_code == 200
    assert resp.json()["skipped"] >= 1
