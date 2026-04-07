# Phase 2 — Supplier Discovery Agent (Tavily) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать поток supplier discovery из спеки: Tavily по `Component.search_queries[]`, структурирование кандидатов через OpenRouter, ARQ-задача `discover_suppliers_task`, UI одобрения/отклонения и публичная форма регистрации поставщика по секретной ссылке (токен в env).

**Architecture:** Данные кандидатов хранятся в новой таблице `supplier_candidates` (статусы `pending` → `approved` | `rejected`); одобрение создаёт запись `Supplier` и связи `SupplierCategory` через существующий `service`. Воркер повторяет паттерн `enrich_component_task`: `Job` в БД, идемпотентность через повторный запуск (новые кандидаты можно добавлять с привязкой к `job_id`). Публичные POST-маршруты без JWT, защищены одним секретом `PUBLIC_SUPPLIER_REGISTRATION_TOKEN`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, ARQ, Redis, `openai` (OpenRouter), `tavily-python` (`AsyncTavilyClient`), Next.js App Router, TypeScript.

**Beads:** Эпик `divine_procurement-zxg` — после утверждения плана можно `bd update divine_procurement-zxg --notes="Plan: docs/superpowers/plans/2026-04-07-phase-2-supplier-discovery-agent.md"`.

**Спека:** `docs/superpowers/specs/2026-04-07-procurement-service-design.md` — §4 Flow 2 (Supplier Discovery), §5 строка «Supplier discovery», §7 «Tavily found supplier with no contact info».

---

## File map (new / changed)

| Path | Role |
|------|------|
| `backend/pyproject.toml` | зависимость `tavily-python` |
| `backend/app/config.py` | `tavily_api_key`, `public_supplier_registration_token` |
| `.env.example` | новые переменные |
| `backend/alembic/versions/<rev>_supplier_candidates.py` | миграция |
| `backend/app/supplier_candidates/models.py` | ORM `SupplierCandidate` |
| `backend/app/supplier_candidates/schemas.py` | Pydantic |
| `backend/app/supplier_candidates/service.py` | list, create from registration, approve, reject |
| `backend/app/supplier_candidates/router.py` | authenticated CRUD для кандидатов |
| `backend/app/public_suppliers/router.py` | `POST` регистрации без auth |
| `backend/app/jobs/worker.py` | `discover_suppliers_task`, регистрация в `WorkerSettings.functions` |
| `backend/app/jobs/router.py` | `POST /components/{id}/discover-suppliers` |
| `backend/app/main.py` | подключить роутеры; CORS уже есть |
| `backend/tests/...` | моки Tavily/OpenRouter, API-тесты |
| `frontend/app/suppliers/candidates/page.tsx` | список кандидатов и действия |
| `frontend/app/register/supplier/page.tsx` | публичная форма |
| `frontend/app/components/Layout.tsx` | пункт навигации «Кандидаты» |
| `docker-compose.yml` | без изменений, если все секреты в `.env` |

---

### Task 1: Зависимости и настройки

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Добавить зависимость**

В секцию `dependencies` в `backend/pyproject.toml` добавить строку (рядом с `openai`):

```toml
    "tavily-python>=0.5",
```

- [ ] **Step 2: Расширить Settings**

В `backend/app/config.py` после `openrouter_model`:

```python
    tavily_api_key: str = ""
    public_supplier_registration_token: str = ""
```

- [ ] **Step 3: Пример переменных окружения**

В `.env.example` после блока OpenRouter:

```env
# Tavily (web search for supplier discovery)
TAVILY_API_KEY=tvly-...

# Public supplier self-registration (share this value with partners; required header on POST)
PUBLIC_SUPPLIER_REGISTRATION_TOKEN=change-me-long-random-string
```

- [ ] **Step 4: Установить зависимости локально**

Run:

```bash
cd backend && pip install -e ".[dev]"
```

Expected: install completes without error.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py .env.example
git commit -m "chore: add Tavily and public registration config"
```

---

### Task 2: Миграция `supplier_candidates`

**Files:**
- Create: `backend/alembic/versions/<revision>_supplier_candidates.py` (имя файла подставить из `alembic revision`)

- [ ] **Step 1: Сгенерировать пустую ревизию**

Run:

```bash
cd backend && alembic revision -m "supplier_candidates"
```

- [ ] **Step 2: Заполнить `upgrade` / `downgrade`**

Заменить содержимое сгенерированного файла на логику ниже (импорты и `revision` оставить из шаблона Alembic). **`down_revision`** на момент написания плана: `d72639185693` (файл `add_jobs_table`); перед мержем выполнить `cd backend && alembic heads` и при необходимости поправить на актуальный head.

```python
"""supplier_candidates

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision = ...
# down_revision = ...
# branch_labels = None
# depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_id", sa.UUID(), sa.ForeignKey("components.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "category_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="company"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("completeness", sa.String(20), nullable=False, server_default="incomplete"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_candidates_status"), "supplier_candidates", ["status"], unique=False)
    op.create_index(op.f("ix_supplier_candidates_component_id"), "supplier_candidates", ["component_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_candidates_component_id"), table_name="supplier_candidates")
    op.drop_index(op.f("ix_supplier_candidates_status"), table_name="supplier_candidates")
    op.drop_table("supplier_candidates")
```

- [ ] **Step 3: Применить миграцию к dev-БД**

Run:

```bash
cd backend && alembic upgrade head
```

Expected: `Running upgrade ... -> ..., supplier_candidates`.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): add supplier_candidates table"
```

---

### Task 3: ORM и пакет `supplier_candidates`

**Files:**
- Create: `backend/app/supplier_candidates/__init__.py` (пустой)
- Create: `backend/app/supplier_candidates/models.py`
- Modify: `backend/app/database.py` — если новые модели не подхватываются через `Base.metadata`, убедиться что `SupplierCandidate` импортируется в `env.py` Alembic для autogenerate; для ручной миграции достаточно импорта в `app.database` при необходимости

`backend/app/supplier_candidates/models.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SupplierCandidate(Base):
    __tablename__ = "supplier_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=True
    )
    category_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="company")
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(String(2000))
    completeness: Mapped[str] = mapped_column(String(20), nullable=False, default="incomplete")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Убедиться, что модель импортируется при старте приложения (например `from app.supplier_candidates import models` в `main.py` после создания роутеров или в `app/models.py` если появится единый реэкспорт). Минимально: один импорт в `backend/app/main.py`:

```python
from app.supplier_candidates import models as _supplier_candidate_models  # noqa: F401
```

- [ ] **Step 1: Создать файлы и импорт в `main.py`**

- [ ] **Step 2: Commit**

```bash
git add backend/app/supplier_candidates/ backend/app/main.py
git commit -m "feat: SupplierCandidate ORM model"
```

---

### Task 4: Схемы и сервис кандидатов

**Files:**
- Create: `backend/app/supplier_candidates/schemas.py`
- Create: `backend/app/supplier_candidates/service.py`

`schemas.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SupplierCandidateRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None
    component_id: uuid.UUID | None
    category_ids: list[uuid.UUID]
    name: str
    type: str
    email: str | None
    website: str | None
    phone: str | None
    notes: str | None
    completeness: str
    status: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicSupplierRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(default="company", pattern="^(company|marketplace)$")
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    notes: str | None = None
    category_ids: list[uuid.UUID] = Field(default_factory=list)
```

`service.py` (основные функции; импорты подправить при необходимости):

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.supplier_candidates.models import SupplierCandidate
from app.supplier_candidates.schemas import PublicSupplierRegistration, SupplierCandidateRead
from app.suppliers.schemas import SupplierCreate
from app.suppliers import service as supplier_service


def _completeness(email: str | None, phone: str | None) -> str:
    return "complete" if (email or phone) else "incomplete"


async def list_candidates(
    db: AsyncSession, *, status: str | None = "pending", component_id: uuid.UUID | None = None
) -> list[SupplierCandidate]:
    q = select(SupplierCandidate)
    if status:
        q = q.where(SupplierCandidate.status == status)
    if component_id:
        q = q.where(SupplierCandidate.component_id == component_id)
    q = q.order_by(SupplierCandidate.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_from_registration(
    db: AsyncSession, body: PublicSupplierRegistration
) -> SupplierCandidate:
    c = SupplierCandidate(
        name=body.name,
        type=body.type,
        email=body.email,
        website=body.website,
        phone=body.phone,
        notes=body.notes,
        category_ids=list(body.category_ids),
        completeness=_completeness(body.email, body.phone),
        status="pending",
        source="registration",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def approve_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> uuid.UUID:
    c = await db.get(SupplierCandidate, candidate_id)
    if not c:
        raise ValueError("candidate not found")
    if c.status != "pending":
        raise ValueError("candidate not pending")
    sup = await supplier_service.create_supplier(
        db,
        SupplierCreate(
            name=c.name,
            type=c.type,
            email=c.email,
            website=c.website,
            phone=c.phone,
            notes=c.notes,
        ),
    )
    for cat_id in c.category_ids:
        await supplier_service.assign_category(db, sup.id, cat_id)
    c.status = "approved"
    await db.commit()
    return sup.id


async def reject_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> None:
    c = await db.get(SupplierCandidate, candidate_id)
    if not c:
        raise ValueError("candidate not found")
    c.status = "rejected"
    await db.commit()
```

Добавить функцию `insert_agent_candidates(db, job_id, component_id, category_ids, rows: list[dict])` которая создаёт записи `SupplierCandidate` с `source="agent"` — вызывать из воркера (см. Task 5). Реализация: цикл по `rows`, для каждого `SupplierCandidate(...)` с полями из JSON OpenRouter.

- [ ] **Step 1: Реализовать `insert_agent_candidates` в `service.py`** с параметром `rows: list[dict]` где каждый dict имеет ключи `name`, `type`, `email`, `website`, `phone`, `notes` (опционально).

- [ ] **Step 2: Commit**

```bash
git add backend/app/supplier_candidates/schemas.py backend/app/supplier_candidates/service.py
git commit -m "feat: supplier candidate schemas and service"
```

---

### Task 5: Воркер — `discover_suppliers_task`

**Files:**
- Modify: `backend/app/jobs/worker.py`
- (опционально) Create: `backend/app/jobs/discovery.py` — чистые функции для unit-тестов

**Поведение:**
1. Загрузить `Component` по `component_id`. Если нет — `update_job(..., failed, ...)`.
2. Взять `queries = comp.search_queries or []`; если пусто — использовать один запрос из `comp.name_normalized or comp.name_internal`.
3. `AsyncTavilyClient(api_key=settings.tavily_api_key)` — для каждого запроса `await client.search(q, max_results=5, search_depth="basic")` (экономия кредитов; при необходимости позже `advanced`).
4. Собрать список сниппетов: для каждого результата `title`, `url`, `content` (обрезать до ~2000 символов суммарно на батч для LLM).
5. Вызвать `call_openrouter` с промптом: из текста выделить уникальных поставщиков, JSON вида:

```json
{
  "suppliers": [
    {
      "name": "string",
      "website": "url or null",
      "email": "string or null",
      "phone": "string or null",
      "type": "company or marketplace",
      "notes": "string or null"
    }
  ]
}
```

6. Для каждого элемента: `completeness` = `complete` если `email` или `phone`, иначе `incomplete` (спека §7).
7. `category_ids`: если у компонента есть `category_id`, положить `[comp.category_id]` в каждую строку (лист каталога).
8. Вызвать `insert_agent_candidates`, затем `update_job` с `result={"candidate_count": N}`.

**Имя задачи ARQ:** `discover_suppliers_task` (как в эпике beads).

Пример сигнатуры:

```python
async def discover_suppliers_task(ctx: dict, *, component_id: str, job_id: str) -> None:
    ...
```

`WorkerSettings`:

```python
class WorkerSettings:
    functions = [enrich_component_task, discover_suppliers_task]
```

- [ ] **Step 1: Вынести в `discovery.py` функцию `build_tavily_context(results: list[dict]) -> str`** для тестирования без сети.

- [ ] **Step 2: Реализовать `discover_suppliers_task` с мокабельными `AsyncTavilyClient` (патч в тестах).**

- [ ] **Step 3: Commit**

```bash
git add backend/app/jobs/worker.py backend/app/jobs/discovery.py backend/app/supplier_candidates/service.py
git commit -m "feat: discover_suppliers_task with Tavily and OpenRouter"
```

---

### Task 6: API — очередь discovery и кандидаты

**Files:**
- Modify: `backend/app/jobs/router.py`
- Create: `backend/app/supplier_candidates/router.py`
- Create: `backend/app/public_suppliers/router.py`

**`jobs/router.py`** — добавить эндпоинт по аналогии с enrich:

```python
@router.post("/components/{component_id}/discover-suppliers", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_discover_suppliers(component_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job_record = await create_job(db, type="discover_suppliers", payload={"component_id": str(component_id)})
    pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job(
        "discover_suppliers_task",
        component_id=str(component_id),
        job_id=str(job_record.id),
    )
    await pool.aclose()
    return EnqueueResponse(job_id=job_record.id)
```

**`supplier_candidates/router.py`** — префикс `/supplier-candidates`, `Depends(get_current_user)`:

- `GET ""` — query `status`, `component_id`; response `list[SupplierCandidateRead]`
- `POST "/{candidate_id}/approve"` — 200 и `{"supplier_id": "..."}`
- `POST "/{candidate_id}/reject"` — 200 `{"ok": true}`

Обработка ошибок: 404 если кандидат не найден; 400 если не `pending`.

**`public_suppliers/router.py`** — без `get_current_user`:

```python
router = APIRouter(prefix="/public", tags=["public"])

@router.post("/supplier-registration", status_code=status.HTTP_201_CREATED)
async def public_register(
    body: PublicSupplierRegistration,
    db: AsyncSession = Depends(get_db),
    x_registration_token: str | None = Header(None, alias="X-Registration-Token"),
):
    if not x_registration_token or x_registration_token != settings.public_supplier_registration_token:
        raise HTTPException(status_code=401, detail="Invalid registration token")
    if not settings.public_supplier_registration_token:
        raise HTTPException(status_code=503, detail="Registration not configured")
    c = await create_from_registration(db, body)
    return SupplierCandidateRead.model_validate(c)
```

- [ ] **Step 1: Подключить роутеры в `main.py`**

```python
from app.supplier_candidates.router import router as supplier_candidates_router
from app.public_suppliers.router import router as public_suppliers_router

app.include_router(supplier_candidates_router)
app.include_router(public_suppliers_router)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/jobs/router.py backend/app/supplier_candidates/router.py backend/app/public_suppliers/router.py backend/app/main.py
git commit -m "feat: API for discovery enqueue, candidates, public registration"
```

---

### Task 7: Тесты

**Files:**
- Create: `backend/tests/test_discovery.py` — unit-тесты контекста и парсинга (без БД)
- Modify: `backend/tests/test_jobs.py` или новый файл — `test_discover_suppliers_task` с патчами `AsyncTavilyClient` и `call_openrouter`
- Create: `backend/tests/test_supplier_candidates_api.py` — `approve`/`reject`/`list` через `auth_client`; публичный endpoint через `client` без заголовка (401) и с заголовком (201)

Пример проверки публичного маршрута (в фикстуре `client` установить `settings.public_supplier_registration_token` через `monkeypatch` или `patch.object` на время теста):

```python
@pytest.mark.asyncio
async def test_public_registration_requires_token(client, db, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "public_supplier_registration_token", "secret")
    resp = await client.post(
        "/public/supplier-registration",
        json={"name": "ACME", "type": "company", "category_ids": []},
    )
    assert resp.status_code == 401
```

- [ ] **Step 1: Написать тесты и убедиться, что CI-вызовов Tavily/OpenRouter нет.**

Run:

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all passed.

- [ ] **Step 2: Commit**

```bash
git add backend/tests/
git commit -m "test: supplier discovery and candidate APIs"
```

---

### Task 8: Frontend — кандидаты и публичная форма

**Files:**
- Create: `frontend/app/suppliers/candidates/page.tsx`
- Create: `frontend/app/register/supplier/page.tsx` (без `Layout` с боковой навигацией — отдельный минимальный layout для публичной страницы)
- Modify: `frontend/app/components/Layout.tsx` — пункт `{ href: "/suppliers/candidates", label: "Кандидаты" }`

**Страница кандидатов:**
- `GET /supplier-candidates?status=pending` через `apiFetch`
- Таблица: имя, источник (`agent` / `registration`), полнота, email, сайт, кнопки «Одобрить» / «Отклонить`
- Опционально: ссылка «Запустить discovery» с компонентов — на первом этапе достаточно кнопки, если передать `component_id` из query `?component_id=` (пользователь вставляет UUID вручную) или позже добавить кнопку на карточке компонента.

**Публичная страница `/register/supplier`:**
- Поля: name, type, email, website, phone, notes
- `category_ids`: мультивыбор — для простоты первой версии можно пустой список или загрузка `/categories/tree` если есть публичный endpoint; если категории только под auth, оставить пустой массив и текст «категории уточнит менеджер после заявки»
- Заголовок `X-Registration-Token` из `process.env.NEXT_PUBLIC_SUPPLIER_REGISTRATION_TOKEN` (добавить в `.env.example` для фронта)

`.env.example`:

```env
NEXT_PUBLIC_SUPPLIER_REGISTRATION_TOKEN=change-me-long-random-string
```

В `apiFetch` для публичной страницы передавать этот заголовок.

- [ ] **Step 1: Реализовать страницы и переменную окружения.**

- [ ] **Step 2: Commit**

```bash
git add frontend/ .env.example
git commit -m "feat(frontend): supplier candidates review and public registration page"
```

---

## Self-review (чеклист автора плана)

| Спека | Покрытие задачами |
|--------|---------------------|
| Flow 2 agent: Tavily → OpenRouter → review | Task 5, 6, 8 |
| Flow 2 passive: public form | Task 4, 6, 8 |
| AI table «Supplier discovery» | Task 5 |
| Incomplete без контакта | Task 4 (`completeness`), Task 5 |
| Job tracking | Task 5–6 (`discover_suppliers`, существующий `Job`) |

**Пробелы (намеренно вне scope этого плана):** уведомление менеджера о новой заявке (email/push); кнопка «Discovery» на UI карточки компонента без ручного UUID; дедупликация кандидата против уже существующих `Supplier` по домену — можно добавить follow-up issue в beads.

---

## Execution handoff

План сохранён в `docs/superpowers/plans/2026-04-07-phase-2-supplier-discovery-agent.md`.

**Два варианта исполнения:**

1. **Subagent-driven (рекомендуется)** — отдельный агент на каждую задачу, ревью между задачами; обязателен субскилл subagent-driven-development.

2. **Inline** — выполнение в одной сессии по чекбоксам с чекпоинтами; обязателен субскилл executing-plans.

Какой вариант выбираешь?

После завершения реализации: `bd close divine_procurement-zxg` (или разбить эпик на подзадачи `bd create` и закрывать по мере готовности), `bd dolt push`, `git push`.
