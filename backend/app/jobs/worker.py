import asyncio
import json
import uuid

from arq.connections import RedisSettings
from openai import AsyncOpenAI
from tavily import AsyncTavilyClient

from app.config import settings
from app.database import AsyncSessionLocal
from app.jobs.discovery import build_tavily_context, flatten_tavily_results

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
    raw = response.choices[0].message.content
    if not raw:
        return {}
    return json.loads(raw)


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


async def discover_suppliers_task(ctx: dict, *, component_id: str, job_id: str) -> None:
    from app.components.models import Component
    from app.jobs.service import update_job
    from app.supplier_candidates.service import insert_agent_candidates

    jid = uuid.UUID(job_id)
    cid = uuid.UUID(component_id)

    if not settings.tavily_api_key:
        async with AsyncSessionLocal() as db:
            await update_job(db, jid, "failed", error="TAVILY_API_KEY is not configured")
        return

    async with AsyncSessionLocal() as db:
        comp = await db.get(Component, cid)
        if not comp:
            await update_job(db, jid, "failed", error="Component not found")
            return
        queries = list(comp.search_queries or [])
        if not queries:
            fallback = (comp.name_normalized or comp.name_internal or "").strip()
            if not fallback:
                await update_job(db, jid, "failed", error="No search queries or name for component")
                return
            queries = [fallback]
        queries = queries[:5]
        category_id = comp.category_id

    try:
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        search_tasks = [client.search(q, max_results=5, search_depth="basic") for q in queries]
        tavily_responses = await asyncio.gather(*search_tasks)
    except Exception as e:
        async with AsyncSessionLocal() as db:
            await update_job(db, jid, "failed", error=f"Tavily search failed: {e}")
        return

    items = flatten_tavily_results(list(tavily_responses))
    context = build_tavily_context(items)
    if not context.strip():
        async with AsyncSessionLocal() as db:
            await update_job(db, jid, "failed", error="Tavily returned no usable results")
        return

    prompt = f"""From the following web search snippets, extract distinct electronics/industrial suppliers or distributors.
Return JSON with exactly this shape:
{{
  "suppliers": [
    {{
      "name": "legal or brand name",
      "website": "https://... or null",
      "email": "string or null",
      "phone": "string or null",
      "type": "company or marketplace",
      "notes": "short note or null"
    }}
  ]
}}

Snippets:
{context}
"""

    try:
        parsed = await call_openrouter(prompt)
        suppliers = parsed.get("suppliers") if isinstance(parsed.get("suppliers"), list) else []
        rows = [s for s in suppliers if isinstance(s, dict)]
    except Exception as e:
        async with AsyncSessionLocal() as db:
            await update_job(db, jid, "failed", error=f"OpenRouter extraction failed: {e}")
        return

    cat_ids: list[uuid.UUID] = []
    if category_id:
        cat_ids = [category_id]

    async with AsyncSessionLocal() as db:
        n = await insert_agent_candidates(
            db,
            job_id=jid,
            component_id=cid,
            category_ids=cat_ids,
            rows=rows,
        )
        await update_job(db, jid, "done", result={"candidate_count": n})


class WorkerSettings:
    functions = [enrich_component_task, discover_suppliers_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 5
