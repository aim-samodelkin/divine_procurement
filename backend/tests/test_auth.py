import pytest


@pytest.mark.asyncio
async def test_login_success(client, db):
    from app.auth.service import create_user
    await create_user(db, email="admin@test.com", password="secret123")
    resp = await client.post("/auth/login", json={"email": "admin@test.com", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    resp = await client.post("/auth/login", json={"email": "admin@test.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_token(client, db):
    from app.auth.service import create_user, create_access_token
    user = await create_user(db, email="me@test.com", password="secret123")
    token = create_access_token({"sub": str(user.id)})
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
