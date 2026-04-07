import pytest


@pytest.mark.asyncio
async def test_create_root_category(auth_client):
    resp = await auth_client.post("/categories", json={"name": "Силовая электроника"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Силовая электроника"
    assert data["parent_id"] is None


@pytest.mark.asyncio
async def test_create_subcategory(auth_client):
    parent = await auth_client.post("/categories", json={"name": "Parent"})
    parent_id = parent.json()["id"]
    child = await auth_client.post("/categories", json={"name": "Child", "parent_id": parent_id})
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_get_tree(auth_client):
    resp = await auth_client.get("/categories/tree")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_delete_category_with_children_fails(auth_client):
    parent = await auth_client.post("/categories", json={"name": "P"})
    pid = parent.json()["id"]
    await auth_client.post("/categories", json={"name": "C", "parent_id": pid})
    resp = await auth_client.delete(f"/categories/{pid}")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_is_leaf(auth_client):
    root = await auth_client.post("/categories", json={"name": "Root"})
    rid = root.json()["id"]
    # no children → is leaf
    resp = await auth_client.get(f"/categories/{rid}")
    assert resp.json()["is_leaf"] is True
    # add child → no longer leaf
    await auth_client.post("/categories", json={"name": "Sub", "parent_id": rid})
    resp = await auth_client.get(f"/categories/{rid}")
    assert resp.json()["is_leaf"] is False
