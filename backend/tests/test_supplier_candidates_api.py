import pytest


@pytest.mark.asyncio
async def test_public_registration_requires_token(client, db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "public_supplier_registration_token", "secret")
    resp = await client.post(
        "/public/supplier-registration",
        json={"name": "ACME", "type": "company", "category_ids": []},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_public_registration_success(client, db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "public_supplier_registration_token", "secret")
    resp = await client.post(
        "/public/supplier-registration",
        json={"name": "ACME", "type": "company", "email": "a@b.co", "category_ids": []},
        headers={"X-Registration-Token": "secret"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ACME"
    assert data["source"] == "registration"
    assert data["completeness"] == "complete"


@pytest.mark.asyncio
async def test_public_registration_not_configured(client, db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "public_supplier_registration_token", "")
    resp = await client.post(
        "/public/supplier-registration",
        json={"name": "ACME", "type": "company", "category_ids": []},
        headers={"X-Registration-Token": "anything"},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_list_and_reject_candidate(auth_client, db):
    from app.config import settings
    from app.supplier_candidates.models import SupplierCandidate

    c = SupplierCandidate(
        name="X",
        type="company",
        completeness="incomplete",
        status="pending",
        source="registration",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    r = await auth_client.get("/supplier-candidates?status=pending")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r2 = await auth_client.post(f"/supplier-candidates/{c.id}/reject")
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_approve_candidate(auth_client, db):
    from app.supplier_candidates.models import SupplierCandidate

    c = SupplierCandidate(
        name="Approved Co",
        type="company",
        email="x@y.z",
        completeness="complete",
        status="pending",
        source="registration",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    r = await auth_client.post(f"/supplier-candidates/{c.id}/approve")
    assert r.status_code == 200
    assert "supplier_id" in r.json()
