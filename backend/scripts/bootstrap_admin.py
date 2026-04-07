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
from app.auth.service import create_user, hash_password
from app.database import AsyncSessionLocal


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


async def main() -> None:
    email_raw = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email_raw or not password:
        return

    email = email_raw.lower()
    sync_password = _truthy_env("BOOTSTRAP_ADMIN_SYNC_PASSWORD")

    async with AsyncSessionLocal() as db:
        n = await db.scalar(select(func.count()).select_from(User))
        if n == 0:
            await create_user(db, email=email, password=password)
            print(f"[bootstrap_admin] created user {email}", flush=True)
            return

        if sync_password:
            result = await db.execute(select(User).where(func.lower(User.email) == email))
            user = result.scalar_one_or_none()
            if user:
                user.hashed_password = hash_password(password)
                await db.commit()
                print(f"[bootstrap_admin] updated password for {email}", flush=True)
            else:
                print(
                    f"[bootstrap_admin] SYNC_PASSWORD: no user with email {email} (create manually or clear users)",
                    flush=True,
                )
            return


if __name__ == "__main__":
    asyncio.run(main())
