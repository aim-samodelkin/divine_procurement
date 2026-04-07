import os

from arq.connections import RedisSettings


class WorkerSettings:
    """Minimal ARQ worker config so `docker compose` can start the worker service."""

    functions = []
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://redis:6379")
    )
