import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_enqueue_enrichment(auth_client, db):
    from app.categories.schemas import CategoryCreate
    from app.categories.service import create_category
    from app.components.schemas import ComponentCreate
    from app.components.service import create_component
    cat = await create_category(db, CategoryCreate(name="EnrichCat"))
    comp = await create_component(db, ComponentCreate(name_internal="Конд. 100/400", category_id=cat.id))

    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()
    mock_pool.aclose = AsyncMock()

    with patch("arq.create_pool", return_value=mock_pool):
        resp = await auth_client.post(f"/components/{comp.id}/enrich")
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data


@pytest.mark.asyncio
async def test_get_job_status(auth_client, db):
    from app.jobs.service import create_job
    job = await create_job(db, type="enrich_component", payload={"component_id": "test"})
    resp = await auth_client.get(f"/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_enrich_component_task_mock():
    """Test the enrichment task logic with mocked OpenRouter."""
    from app.jobs.worker import enrich_component_task

    mock_result = {
        "name_normalized": "Конденсатор электролитический 100 мкФ 400 В",
        "search_queries": ["конденсатор 100мкФ 400В купить", "capacitor 100uF 400V supplier Russia"],
        "category_suggestion": "Пассивные компоненты / Конденсаторы",
    }

    component_uuid = "12345678-1234-5678-1234-567812345678"
    job_uuid = "87654321-4321-8765-4321-876543218765"

    with patch("app.jobs.worker.call_openrouter", new_callable=AsyncMock, return_value=mock_result):
        with patch("app.jobs.worker.AsyncSessionLocal") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_db.get.return_value = AsyncMock(
                id=component_uuid, name_internal="Конд. 100/400",
                name_normalized=None, search_queries=[], enrichment_status="pending"
            )

            await enrich_component_task(ctx={}, component_id=component_uuid, job_id=job_uuid)
