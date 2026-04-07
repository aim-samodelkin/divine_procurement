import json
import uuid

from arq.connections import RedisSettings
from openai import AsyncOpenAI

from app.config import settings
from app.database import AsyncSessionLocal

openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)


async def call_openrouter(prompt: str) -> dict:
    response = await openrouter_client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a procurement assistant. "
                    "Respond only with valid JSON, no markdown, no explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


async def enrich_component_task(ctx: dict, *, component_id: str, job_id: str) -> None:
    from app.jobs.service import update_job

    async with AsyncSessionLocal() as db:
        from app.components.models import Component
        comp = await db.get(Component, uuid.UUID(component_id))
        if not comp:
            await update_job(db, uuid.UUID(job_id), "failed", error="Component not found")
            return

        try:
            prompt = f"""
Normalize this component name for procurement search in Russia.
Component: "{comp.name_internal}"

Return JSON with exactly these keys:
{{
  "name_normalized": "full clear name with specs",
  "search_queries": ["query 1 in Russian", "query 2 in English"],
  "category_suggestion": "Category / Subcategory path"
}}
"""
            result = await call_openrouter(prompt)
            comp.name_normalized = result.get("name_normalized", comp.name_internal)
            comp.search_queries = result.get("search_queries", [])
            comp.enrichment_status = "in_review"
            await db.commit()
            await update_job(db, uuid.UUID(job_id), "done", result=result)
        except Exception as e:
            await update_job(db, uuid.UUID(job_id), "failed", error=str(e))


class WorkerSettings:
    functions = [enrich_component_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 5
