"""Set password for an existing user (reads password from env)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import func, select

from app.auth.models import User
from app.auth.service import create_user, hash_password
from app.database import AsyncSessionLocal


async def main() -> None:
    argv = [a for a in sys.argv[1:] if a != "--create"]
    allow_create = "--create" in sys.argv[1:]

    if len(argv) < 1:
        print("Usage: python scripts/reset_password.py [--create] <email> [password]", flush=True)
        print("Password: second arg, or NEW_PASSWORD / BOOTSTRAP_ADMIN_PASSWORD env.", flush=True)
        print("--create: create the user if missing (empty DB / bootstrap env not passed into container).", flush=True)
        sys.exit(1)

    email = argv[0].strip().lower()
    password = (
        (argv[1] if len(argv) > 1 else None)
        or os.environ.get("NEW_PASSWORD")
        or os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    )
    if not password:
        print("Set NEW_PASSWORD or BOOTSTRAP_ADMIN_PASSWORD in the environment.", flush=True)
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(func.lower(User.email) == email))
        user = result.scalar_one_or_none()
        if not user:
            if not allow_create:
                print(f"[reset_password] no user with email {email}", flush=True)
                print("Hint: run with --create to add this user, or fix BOOTSTRAP_* in docker-compose / .env", flush=True)
                sys.exit(1)
            await create_user(db, email=email, password=password)
            print(f"[reset_password] created user {email}", flush=True)
            return
        user.hashed_password = hash_password(password)
        await db.commit()
        print(f"[reset_password] password updated for {email}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
