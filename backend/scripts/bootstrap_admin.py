"""Create first admin user when BOOTSTRAP_ADMIN_* env vars are set (empty DB only)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Run from /app in Docker
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import func, select

from app.auth.models import User
from app.auth.service import create_user
from app.database import AsyncSessionLocal


async def main() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or not password:
        return

    async with AsyncSessionLocal() as db:
        n = await db.scalar(select(func.count()).select_from(User))
        if n and n > 0:
            return
        await create_user(db, email=email, password=password)
        print(f"[bootstrap_admin] created user {email}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
