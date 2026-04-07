import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connection(db):
    result = await db.execute(text("SELECT 1"))
    assert result.scalar() == 1
