# Procurement Service — Phase 1: Foundation, Component Enrichment & Supplier Management

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully working web application with auth, hierarchical category tree, component catalog with AI enrichment, and supplier management with coverage dashboard — the foundation all later phases depend on.

**Architecture:** Modular monolith. FastAPI backend with PostgreSQL (SQLAlchemy 2.0 + Alembic). Next.js 14 App Router frontend. ARQ worker for async AI tasks (OpenRouter). All services in Docker Compose. Auth via JWT (access + refresh tokens).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pydantic-settings, python-jose, passlib[bcrypt], python-multipart, ARQ, openai (for OpenRouter), Next.js 14, TypeScript, Tailwind CSS, PostgreSQL 16, Redis 7, Docker Compose

---

## File Structure

```
docker-compose.yml
.env.example

backend/
  pyproject.toml
  alembic.ini
  alembic/
    env.py
    versions/
      0001_initial_schema.py
  app/
    __init__.py
    main.py                  # FastAPI app, router registration, CORS
    config.py                # Settings via pydantic-settings
    database.py              # SQLAlchemy engine + session dependency
    auth/
      __init__.py
      models.py              # User ORM model
      schemas.py             # Pydantic schemas: UserCreate, Token, etc.
      service.py             # hash_password, verify_password, create_token
      router.py              # POST /auth/login, POST /auth/refresh, GET /auth/me
      deps.py                # get_current_user FastAPI dependency
    categories/
      __init__.py
      models.py              # Category ORM model (self-referencing parent_id)
      schemas.py             # CategoryCreate, CategoryRead, CategoryTree
      service.py             # CRUD, tree builder, leaf detection
      router.py              # GET/POST/PATCH/DELETE /categories, GET /categories/tree
    components/
      __init__.py
      models.py              # Component ORM model
      schemas.py             # ComponentCreate, ComponentRead, ComponentUpdate
      service.py             # CRUD, CSV import parsing
      router.py              # GET/POST/PATCH/DELETE /components, POST /components/import
    suppliers/
      __init__.py
      models.py              # Supplier, SupplierCategory ORM models
      schemas.py             # SupplierCreate, SupplierRead, SupplierWithCategories
      service.py             # CRUD, coverage calculation
      router.py              # CRUD /suppliers, GET /suppliers/coverage
    jobs/
      __init__.py
      models.py              # Job ORM model
      schemas.py             # JobRead
      service.py             # create_job, update_job_status
      worker.py              # ARQ worker: enrich_component task
      router.py              # GET /jobs/{id}
  tests/
    conftest.py              # pytest fixtures: test DB, test client, auth headers
    test_auth.py
    test_categories.py
    test_components.py
    test_suppliers.py
    test_jobs.py

frontend/
  package.json
  next.config.ts
  tsconfig.json
  tailwind.config.ts
  src/
    app/
      layout.tsx             # Root layout with nav
      page.tsx               # Redirect to /dashboard
      login/
        page.tsx
      dashboard/
        page.tsx             # Summary cards: components, suppliers, coverage alerts
      categories/
        page.tsx             # Category tree with add/edit/delete
      components/
        page.tsx             # Component table with enrichment status + CSV import
        review/
          page.tsx           # Enrichment review screen (approve/correct categories)
      suppliers/
        page.tsx             # Supplier list + add form
        coverage/
          page.tsx           # Coverage dashboard per category
    lib/
      api.ts                 # fetch wrapper: base URL, auth headers, error handling
      auth.ts                # login(), logout(), getToken(), isAuthenticated()
    components/
      ui/
        Button.tsx
        Input.tsx
        Table.tsx
        Badge.tsx
        Spinner.tsx
      Layout.tsx             # Sidebar + header shell
      CategoryTree.tsx       # Recursive tree render with inline add/edit
      EnrichmentBadge.tsx    # pending | in_review | enriched status badge
      CoverageBar.tsx        # Horizontal bar with traffic-light color
```

---

## Task 1: Docker Compose + Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/pyproject.toml`
- Create: `frontend/package.json`

- [ ] **Step 1: Create `.env.example`**

```env
# Database
POSTGRES_USER=procurement
POSTGRES_PASSWORD=procurement
POSTGRES_DB=procurement
DATABASE_URL=postgresql+asyncpg://procurement:procurement@postgres:5432/procurement

# Redis
REDIS_URL=redis://redis:6379

# Auth
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-3.5-haiku

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build: ./backend
    command: arq app.jobs.worker.WorkerSettings
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  web:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    env_file: .env
    depends_on:
      - app

volumes:
  postgres_data:
```

- [ ] **Step 3: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "procurement-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic-settings>=2.0",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "python-multipart>=0.0.9",
    "arq>=0.25",
    "openai>=1.40",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "anyio>=4",
]
```

- [ ] **Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[dev]"
COPY . .
```

- [ ] **Step 5: Create `frontend/package.json` and init Next.js**

Run from repo root:
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
```

Then rename `src/` → keep App Router structure. Confirm `package.json` has `next`, `react`, `react-dom`, `typescript`, `tailwindcss`.

- [ ] **Step 6: Verify containers start**

```bash
cp .env.example .env
docker compose up postgres redis -d
docker compose up app --build
```

Expected: FastAPI starts, `http://localhost:8000/docs` shows Swagger UI (empty).

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example backend/pyproject.toml backend/Dockerfile frontend/
git commit -m "feat: project scaffolding — Docker Compose, FastAPI, Next.js"
```

---

## Task 2: Database Setup (SQLAlchemy + Alembic)

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/config.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-haiku"


settings = Settings()
```

- [ ] **Step 2: Create `backend/app/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 3: Set up Alembic**

```bash
cd backend
alembic init alembic
```

Edit `alembic/env.py` — replace the generated file with:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base

# Import all models so Alembic sees them
import app.auth.models  # noqa: F401
import app.categories.models  # noqa: F401
import app.components.models  # noqa: F401
import app.suppliers.models  # noqa: F401
import app.jobs.models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


asyncio.run(run_migrations_online())
```

Edit `alembic.ini` — set:
```ini
script_location = alembic
sqlalchemy.url = # leave empty, set in env.py
```

- [ ] **Step 4: Write test to verify DB connection**

Create `backend/tests/conftest.py`:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

Create `backend/tests/test_db.py`:

```python
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connection(db):
    result = await db.execute(text("SELECT 1"))
    assert result.scalar() == 1
```

- [ ] **Step 5: Run test to verify it fails (no models yet)**

```bash
cd backend
pytest tests/test_db.py -v
```

Expected: FAIL — tables don't exist yet.

- [ ] **Step 6: Create initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
```

This generates `alembic/versions/0001_initial_schema.py`. Run it:

```bash
alembic upgrade head
```

- [ ] **Step 7: Run test — must pass now**

```bash
pytest tests/test_db.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/alembic/ backend/tests/
git commit -m "feat: database setup — SQLAlchemy async + Alembic migrations"
```

---

## Task 3: Auth Module

**Files:**
- Create: `backend/app/auth/models.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/auth/deps.py`
- Create: `backend/app/main.py`
- Modify: `backend/alembic/versions/` (regenerate migration)
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auth.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_login_success(client, db):
    from app.auth.service import create_user
    await create_user(db, email="admin@test.com", password="secret123")
    resp = await client.post("/auth/login", json={"email": "admin@test.com", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    resp = await client.post("/auth/login", json={"email": "admin@test.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_token(client, db):
    from app.auth.service import create_user, create_access_token
    user = await create_user(db, email="me@test.com", password="secret123")
    token = create_access_token({"sub": str(user.id)})
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
```

- [ ] **Step 2: Run tests — must fail**

```bash
pytest tests/test_auth.py -v
```

Expected: FAIL — modules not found.

- [ ] **Step 3: Create `backend/app/auth/models.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Create `backend/app/auth/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Create `backend/app/auth/service.py`**

```python
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({**data, "exp": expire, "type": "access"}, settings.secret_key, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode({**data, "exp": expire, "type": "refresh"}, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


async def create_user(db: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

- [ ] **Step 6: Create `backend/app/auth/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import decode_token, get_user_by_id
from app.database import get_db

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

- [ ] **Step 7: Create `backend/app/auth/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.schemas import LoginRequest, TokenResponse, UserRead
from app.auth.service import authenticate_user, create_access_token, create_refresh_token, decode_token
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: dict, db: AsyncSession = Depends(get_db)):
    from jose import JWTError
    try:
        payload = decode_token(body.get("refresh_token", ""))
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(
        access_token=create_access_token({"sub": user_id}),
        refresh_token=create_refresh_token({"sub": user_id}),
    )


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 8: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router

app = FastAPI(title="Procurement Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
```

- [ ] **Step 9: Generate and run migration**

```bash
cd backend
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

Also create the test database:
```bash
psql -U procurement -c "CREATE DATABASE procurement_test;"
```

- [ ] **Step 10: Run tests — must pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 11: Commit**

```bash
git add backend/app/auth/ backend/app/main.py backend/alembic/ backend/tests/
git commit -m "feat: auth module — JWT login, refresh, get_current_user"
```

---

## Task 4: Category API (Hierarchical Tree)

**Files:**
- Create: `backend/app/categories/models.py`
- Create: `backend/app/categories/schemas.py`
- Create: `backend/app/categories/service.py`
- Create: `backend/app/categories/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_categories.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_categories.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_root_category(auth_client):
    resp = await auth_client.post("/categories", json={"name": "Силовая электроника"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Силовая электроника"
    assert data["parent_id"] is None


@pytest.mark.asyncio
async def test_create_subcategory(auth_client):
    parent = await auth_client.post("/categories", json={"name": "Parent"})
    parent_id = parent.json()["id"]
    child = await auth_client.post("/categories", json={"name": "Child", "parent_id": parent_id})
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_get_tree(auth_client):
    resp = await auth_client.get("/categories/tree")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_delete_category_with_children_fails(auth_client):
    parent = await auth_client.post("/categories", json={"name": "P"})
    pid = parent.json()["id"]
    await auth_client.post("/categories", json={"name": "C", "parent_id": pid})
    resp = await auth_client.delete(f"/categories/{pid}")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_is_leaf(auth_client):
    root = await auth_client.post("/categories", json={"name": "Root"})
    rid = root.json()["id"]
    # no children → is leaf
    resp = await auth_client.get(f"/categories/{rid}")
    assert resp.json()["is_leaf"] is True
    # add child → no longer leaf
    await auth_client.post("/categories", json={"name": "Sub", "parent_id": rid})
    resp = await auth_client.get(f"/categories/{rid}")
    assert resp.json()["is_leaf"] is False
```

Add `auth_client` fixture to `conftest.py`:

```python
@pytest_asyncio.fixture
async def auth_client(client, db):
    from app.auth.service import create_user, create_access_token
    user = await create_user(db, email="fixture@test.com", password="pass")
    token = create_access_token({"sub": str(user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

- [ ] **Step 2: Run tests — must fail**

```bash
pytest tests/test_categories.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create `backend/app/categories/models.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped["Category | None"] = relationship("Category", remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent")
```

- [ ] **Step 4: Create `backend/app/categories/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    is_leaf: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryTree(CategoryRead):
    children: list["CategoryTree"] = []
```

- [ ] **Step 5: Create `backend/app/categories/service.py`**

```python
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.categories.schemas import CategoryCreate, CategoryTree, CategoryUpdate


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    if data.parent_id:
        parent = await db.get(Category, data.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
    cat = Category(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Category:
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


async def is_leaf(db: AsyncSession, category_id: uuid.UUID) -> bool:
    result = await db.execute(select(Category).where(Category.parent_id == category_id).limit(1))
    return result.scalar_one_or_none() is None


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
    cat = await get_category(db, category_id)
    if not await is_leaf(db, category_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete category with children")
    await db.delete(cat)
    await db.commit()


async def get_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category))
    return list(result.scalars().all())


async def build_tree(db: AsyncSession) -> list[CategoryTree]:
    all_cats = await get_all_categories(db)
    leaf_set = {c.id for c in all_cats}
    for c in all_cats:
        if c.parent_id in leaf_set:
            leaf_set.discard(c.parent_id)

    cat_map: dict[uuid.UUID, CategoryTree] = {}
    for c in all_cats:
        node = CategoryTree(
            id=c.id, name=c.name, description=c.description,
            parent_id=c.parent_id, is_leaf=(c.id in leaf_set),
            created_at=c.created_at,
        )
        cat_map[c.id] = node

    roots = []
    for node in cat_map.values():
        if node.parent_id is None:
            roots.append(node)
        elif node.parent_id in cat_map:
            cat_map[node.parent_id].children.append(node)
    return roots
```

- [ ] **Step 6: Create `backend/app/categories/router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.categories import service
from app.categories.schemas import CategoryCreate, CategoryRead, CategoryTree, CategoryUpdate
from app.database import get_db

router = APIRouter(prefix="/categories", tags=["categories"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    cat = await service.create_category(db, body)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.get("/tree", response_model=list[CategoryTree])
async def get_tree(db: AsyncSession = Depends(get_db)):
    return await service.build_tree(db)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category(db, category_id)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(category_id: uuid.UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category(db, category_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    leaf = await service.is_leaf(db, cat.id)
    return CategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        parent_id=cat.parent_id, is_leaf=leaf, created_at=cat.created_at,
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await service.delete_category(db, category_id)
```

- [ ] **Step 7: Register router in `backend/app/main.py`**

```python
from app.categories.router import router as categories_router
# ... existing imports

app.include_router(auth_router)
app.include_router(categories_router)
```

- [ ] **Step 8: Generate migration and run**

```bash
alembic revision --autogenerate -m "add categories table"
alembic upgrade head
```

Also run against test DB:
```bash
DATABASE_URL=postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test alembic upgrade head
```

- [ ] **Step 9: Run tests — must pass**

```bash
pytest tests/test_categories.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/app/categories/ backend/app/main.py backend/alembic/ backend/tests/
git commit -m "feat: category API — hierarchical tree, CRUD, leaf detection"
```

---

## Task 5: Component API + CSV Import

**Files:**
- Create: `backend/app/components/models.py`
- Create: `backend/app/components/schemas.py`
- Create: `backend/app/components/service.py`
- Create: `backend/app/components/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_components.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_components.py`:

```python
import io
import pytest


@pytest.mark.asyncio
async def test_create_component(auth_client, db):
    from app.categories.service import create_category
    from app.categories.schemas import CategoryCreate
    cat = await create_category(db, CategoryCreate(name="TestCat"))
    resp = await auth_client.post("/components", json={"name_internal": "Конд. 100мкФ", "category_id": str(cat.id)})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name_internal"] == "Конд. 100мкФ"
    assert data["enrichment_status"] == "pending"


@pytest.mark.asyncio
async def test_list_components(auth_client):
    resp = await auth_client.get("/components")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_csv_import(auth_client, db):
    from app.categories.service import create_category
    from app.categories.schemas import CategoryCreate
    cat = await create_category(db, CategoryCreate(name="CSVCat"))
    csv_content = f"name_internal,category_id\nКомпонент A,{cat.id}\nКомпонент B,{cat.id}\n"
    files = {"file": ("components.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await auth_client.post("/components/import", files=files)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 2


@pytest.mark.asyncio
async def test_csv_import_invalid_rows_skipped(auth_client):
    csv_content = "name_internal,category_id\n,invalid-uuid\nValid Name,00000000-0000-0000-0000-000000000000\n"
    files = {"file": ("components.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await auth_client.post("/components/import", files=files)
    assert resp.status_code == 200
    assert resp.json()["skipped"] >= 1
```

- [ ] **Step 2: Run tests — must fail**

```bash
pytest tests/test_components.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create `backend/app/components/models.py`**

```python
import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

EnrichmentStatus = Literal["pending", "in_review", "enriched"]


class Component(Base):
    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_internal: Mapped[str] = mapped_column(String(500), nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    search_queries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    enrichment_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped["Category | None"] = relationship("Category")  # type: ignore[name-defined]
```

- [ ] **Step 4: Create `backend/app/components/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class ComponentCreate(BaseModel):
    name_internal: str
    description: str | None = None
    category_id: uuid.UUID | None = None


class ComponentUpdate(BaseModel):
    name_internal: str | None = None
    name_normalized: str | None = None
    description: str | None = None
    search_queries: list[str] | None = None
    category_id: uuid.UUID | None = None
    enrichment_status: str | None = None


class ComponentRead(BaseModel):
    id: uuid.UUID
    name_internal: str
    name_normalized: str | None
    description: str | None
    search_queries: list[str]
    category_id: uuid.UUID | None
    enrichment_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
```

- [ ] **Step 5: Create `backend/app/components/service.py`**

```python
import csv
import io
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models import Component
from app.components.schemas import ComponentCreate, ImportResult


async def create_component(db: AsyncSession, data: ComponentCreate) -> Component:
    comp = Component(**data.model_dump())
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp


async def list_components(db: AsyncSession, category_id: uuid.UUID | None = None) -> list[Component]:
    q = select(Component)
    if category_id:
        q = q.where(Component.category_id == category_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_component(db: AsyncSession, component_id: uuid.UUID) -> Component | None:
    return await db.get(Component, component_id)


async def import_from_csv(db: AsyncSession, content: bytes) -> ImportResult:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    imported, skipped, errors = 0, 0, []

    for i, row in enumerate(reader, start=2):
        name = (row.get("name_internal") or "").strip()
        cat_str = (row.get("category_id") or "").strip()
        if not name:
            skipped += 1
            errors.append(f"Row {i}: missing name_internal")
            continue
        cat_id = None
        if cat_str:
            try:
                cat_id = uuid.UUID(cat_str)
            except ValueError:
                skipped += 1
                errors.append(f"Row {i}: invalid category_id '{cat_str}'")
                continue
        db.add(Component(name_internal=name, category_id=cat_id))
        imported += 1

    await db.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=errors)
```

- [ ] **Step 6: Create `backend/app/components/router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.components import service
from app.components.schemas import ComponentCreate, ComponentRead, ComponentUpdate, ImportResult
from app.database import get_db

router = APIRouter(prefix="/components", tags=["components"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ComponentRead])
async def list_components(category_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    return await service.list_components(db, category_id)


@router.post("", response_model=ComponentRead, status_code=status.HTTP_201_CREATED)
async def create_component(body: ComponentCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_component(db, body)


@router.patch("/{component_id}", response_model=ComponentRead)
async def update_component(component_id: uuid.UUID, body: ComponentUpdate, db: AsyncSession = Depends(get_db)):
    comp = await service.get_component(db, component_id)
    if not comp:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Component not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(comp, k, v)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.post("/import", response_model=ImportResult)
async def import_components(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    return await service.import_from_csv(db, content)
```

- [ ] **Step 7: Register router, run migration, run tests**

Add to `backend/app/main.py`:
```python
from app.components.router import router as components_router
app.include_router(components_router)
```

```bash
alembic revision --autogenerate -m "add components table"
alembic upgrade head
DATABASE_URL=postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test alembic upgrade head
pytest tests/test_components.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/components/ backend/app/main.py backend/alembic/ backend/tests/
git commit -m "feat: component catalog API — CRUD + CSV import"
```

---

## Task 6: Supplier API + Coverage

**Files:**
- Create: `backend/app/suppliers/models.py`
- Create: `backend/app/suppliers/schemas.py`
- Create: `backend/app/suppliers/service.py`
- Create: `backend/app/suppliers/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_suppliers.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_suppliers.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_supplier(auth_client):
    resp = await auth_client.post("/suppliers", json={
        "name": "ООО Поставщик", "type": "company", "email": "s@example.com"
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "company"


@pytest.mark.asyncio
async def test_create_marketplace_supplier(auth_client):
    resp = await auth_client.post("/suppliers", json={
        "name": "ChipDip", "type": "marketplace", "website": "https://chipdip.ru"
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "marketplace"


@pytest.mark.asyncio
async def test_assign_category(auth_client, db):
    from app.categories.schemas import CategoryCreate
    from app.categories.service import create_category
    cat = await create_category(db, CategoryCreate(name="Electronics"))
    supplier = await auth_client.post("/suppliers", json={"name": "S", "type": "company"})
    sid = supplier.json()["id"]
    resp = await auth_client.post(f"/suppliers/{sid}/categories", json={"category_id": str(cat.id)})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_coverage_returns_categories(auth_client, db):
    resp = await auth_client.get("/suppliers/coverage")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run tests — must fail**

```bash
pytest tests/test_suppliers.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create `backend/app/suppliers/models.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # company | marketplace
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category_links: Mapped[list["SupplierCategory"]] = relationship("SupplierCategory", back_populates="supplier", cascade="all, delete-orphan")


class SupplierCategory(Base):
    __tablename__ = "supplier_categories"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="category_links")
```

- [ ] **Step 4: Create `backend/app/suppliers/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class SupplierCreate(BaseModel):
    name: str
    type: str  # company | marketplace
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    notes: str | None = None


class SupplierRead(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    email: str | None
    website: str | None
    phone: str | None
    notes: str | None
    category_ids: list[uuid.UUID] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignCategoryRequest(BaseModel):
    category_id: uuid.UUID


class CoverageItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    supplier_count: int
    status: str  # red | yellow | green
```

- [ ] **Step 5: Create `backend/app/suppliers/service.py`**

```python
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.categories.models import Category
from app.suppliers.models import Supplier, SupplierCategory
from app.suppliers.schemas import CoverageItem, SupplierCreate


async def create_supplier(db: AsyncSession, data: SupplierCreate) -> Supplier:
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def get_suppliers(db: AsyncSession) -> list[Supplier]:
    result = await db.execute(select(Supplier).options(selectinload(Supplier.category_links)))
    return list(result.scalars().all())


async def assign_category(db: AsyncSession, supplier_id: uuid.UUID, category_id: uuid.UUID) -> None:
    link = SupplierCategory(supplier_id=supplier_id, category_id=category_id)
    db.add(link)
    await db.commit()


async def get_coverage(db: AsyncSession) -> list[CoverageItem]:
    # Count suppliers per category
    count_q = (
        select(SupplierCategory.category_id, func.count(SupplierCategory.supplier_id).label("cnt"))
        .group_by(SupplierCategory.category_id)
        .subquery()
    )
    result = await db.execute(
        select(Category.id, Category.name, count_q.c.cnt)
        .outerjoin(count_q, Category.id == count_q.c.category_id)
    )
    items = []
    for row in result.all():
        cnt = row.cnt or 0
        if cnt < 2:
            status = "red"
        elif cnt < 4:
            status = "yellow"
        else:
            status = "green"
        items.append(CoverageItem(category_id=row.id, category_name=row.name, supplier_count=cnt, status=status))
    return items
```

- [ ] **Step 6: Create `backend/app/suppliers/router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.suppliers import service
from app.suppliers.schemas import AssignCategoryRequest, CoverageItem, SupplierCreate, SupplierRead
from app.database import get_db

router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[SupplierRead])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    suppliers = await service.get_suppliers(db)
    result = []
    for s in suppliers:
        result.append(SupplierRead(
            id=s.id, name=s.name, type=s.type, email=s.email, website=s.website,
            phone=s.phone, notes=s.notes, created_at=s.created_at,
            category_ids=[lnk.category_id for lnk in s.category_links],
        ))
    return result


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db)):
    s = await service.create_supplier(db, body)
    return SupplierRead(
        id=s.id, name=s.name, type=s.type, email=s.email, website=s.website,
        phone=s.phone, notes=s.notes, created_at=s.created_at, category_ids=[],
    )


@router.post("/{supplier_id}/categories")
async def assign_category(supplier_id: uuid.UUID, body: AssignCategoryRequest, db: AsyncSession = Depends(get_db)):
    await service.assign_category(db, supplier_id, body.category_id)
    return {"ok": True}


@router.get("/coverage", response_model=list[CoverageItem])
async def get_coverage(db: AsyncSession = Depends(get_db)):
    return await service.get_coverage(db)
```

- [ ] **Step 7: Register router, migrate, test**

Add to `backend/app/main.py`:
```python
from app.suppliers.router import router as suppliers_router
app.include_router(suppliers_router)
```

```bash
alembic revision --autogenerate -m "add suppliers and supplier_categories tables"
alembic upgrade head
DATABASE_URL=postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test alembic upgrade head
pytest tests/test_suppliers.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/suppliers/ backend/app/main.py backend/alembic/ backend/tests/
git commit -m "feat: supplier API — CRUD, category assignment, coverage"
```

---

## Task 7: ARQ Worker + Component Enrichment (OpenRouter)

**Files:**
- Create: `backend/app/jobs/models.py`
- Create: `backend/app/jobs/schemas.py`
- Create: `backend/app/jobs/service.py`
- Create: `backend/app/jobs/router.py`
- Create: `backend/app/jobs/worker.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_jobs.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_jobs.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_enqueue_enrichment(auth_client, db):
    from app.categories.schemas import CategoryCreate
    from app.categories.service import create_category
    from app.components.schemas import ComponentCreate
    from app.components.service import create_component
    cat = await create_category(db, CategoryCreate(name="EnrichCat"))
    comp = await create_component(db, ComponentCreate(name_internal="Конд. 100/400", category_id=cat.id))

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

    with patch("app.jobs.worker.call_openrouter", new_callable=AsyncMock, return_value=mock_result):
        with patch("app.jobs.worker.AsyncSessionLocal") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_db.get.return_value = AsyncMock(
                id="test-id", name_internal="Конд. 100/400",
                name_normalized=None, search_queries=[], enrichment_status="pending"
            )

            await enrich_component_task(ctx={}, component_id="test-id", job_id="job-id")
```

- [ ] **Step 2: Run tests — must fail**

```bash
pytest tests/test_jobs.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create `backend/app/jobs/models.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 4: Create `backend/app/jobs/schemas.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobRead(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class EnqueueResponse(BaseModel):
    job_id: uuid.UUID
```

- [ ] **Step 5: Create `backend/app/jobs/service.py`**

```python
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job


async def create_job(db: AsyncSession, type: str, payload: dict[str, Any]) -> Job:
    job = Job(type=type, payload=payload)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await db.get(Job, job_id)


async def update_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    job = await db.get(Job, job_id)
    if job:
        job.status = status
        job.result = result
        job.error = error
        if status in ("done", "failed"):
            job.completed_at = datetime.now(timezone.utc)
        await db.commit()
```

- [ ] **Step 6: Create `backend/app/jobs/worker.py`**

```python
import json
import uuid

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
    redis_settings_from_url = settings.redis_url
    max_jobs = 5
```

- [ ] **Step 7: Create `backend/app/jobs/router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.jobs.schemas import EnqueueResponse, JobRead
from app.jobs.service import create_job, get_job
from app.database import get_db

router = APIRouter(tags=["jobs"], dependencies=[Depends(get_current_user)])


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/components/{component_id}/enrich", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_enrichment(component_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    import arq
    job_record = await create_job(db, type="enrich_component", payload={"component_id": str(component_id)})
    pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))  # type: ignore
    await pool.enqueue_job("enrich_component_task", component_id=str(component_id), job_id=str(job_record.id))
    await pool.aclose()
    return EnqueueResponse(job_id=job_record.id)
```

Add missing import in router:
```python
from app.config import settings
```

- [ ] **Step 8: Register router, migrate, test**

Add to `backend/app/main.py`:
```python
from app.jobs.router import router as jobs_router
app.include_router(jobs_router)
```

```bash
alembic revision --autogenerate -m "add jobs table"
alembic upgrade head
DATABASE_URL=postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test alembic upgrade head
pytest tests/test_jobs.py -v
```

Expected: 3 tests PASS (mock test + job status + enqueue).

- [ ] **Step 9: Commit**

```bash
git add backend/app/jobs/ backend/app/main.py backend/alembic/ backend/tests/
git commit -m "feat: ARQ worker + component enrichment task (OpenRouter)"
```

---

## Task 8: Next.js Frontend — Auth + Shell

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Create `frontend/src/lib/api.ts`**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
```

- [ ] **Step 2: Create `frontend/src/lib/auth.ts`**

```typescript
import { apiFetch } from "./api";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export async function login(email: string, password: string): Promise<void> {
  const data = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
}

export function logout(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}
```

- [ ] **Step 3: Create `frontend/src/app/login/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">Закупки</h1>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)} required
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)} required
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit" disabled={loading}
          className="w-full bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Вход..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/Layout.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Дашборд" },
  { href: "/categories", label: "Категории" },
  { href: "/components", label: "Компоненты" },
  { href: "/suppliers", label: "Поставщики" },
  { href: "/suppliers/coverage", label: "Покрытие" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <span className="font-bold text-gray-900">Закупки</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(n => (
            <Link
              key={n.href} href={n.href}
              className={`block px-3 py-2 rounded text-sm font-medium transition-colors ${
                pathname.startsWith(n.href) ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-900 w-full text-left px-3 py-2">
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/src/app/dashboard/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { apiFetch } from "@/lib/api";

interface CoverageItem { category_name: string; supplier_count: number; status: string; }

export default function DashboardPage() {
  const [coverage, setCoverage] = useState<CoverageItem[]>([]);

  useEffect(() => {
    apiFetch<CoverageItem[]>("/suppliers/coverage").then(setCoverage).catch(console.error);
  }, []);

  const redCount = coverage.filter(c => c.status === "red").length;
  const yellowCount = coverage.filter(c => c.status === "yellow").length;

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Дашборд</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий без поставщиков</div>
          <div className="text-3xl font-bold text-red-600 mt-1">{redCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий с малым покрытием</div>
          <div className="text-3xl font-bold text-yellow-500 mt-1">{yellowCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий всего</div>
          <div className="text-3xl font-bold text-gray-900 mt-1">{coverage.length}</div>
        </div>
      </div>
      {redCount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          Категории без поставщиков: {coverage.filter(c => c.status === "red").map(c => c.category_name).join(", ")}
        </div>
      )}
    </Layout>
  );
}
```

- [ ] **Step 6: Update root `app/page.tsx` to redirect**

```tsx
import { redirect } from "next/navigation";
export default function Home() { redirect("/dashboard"); }
```

- [ ] **Step 7: Start frontend and verify**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` — should redirect to `/login`. Log in (create user via API first):
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}'
```

(First, seed a user — add a POST `/auth/register` endpoint temporarily or run `create_user` via a script.)

Temporary seed script `backend/seed.py`:
```python
import asyncio
from app.database import AsyncSessionLocal
from app.auth.service import create_user

async def main():
    async with AsyncSessionLocal() as db:
        await create_user(db, "admin@example.com", "secret123")
    print("Admin user created")

asyncio.run(main())
```

```bash
cd backend && python seed.py
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/ frontend/package.json
git commit -m "feat: Next.js frontend — auth, layout shell, dashboard"
```

---

## Task 9: Category Tree UI

**Files:**
- Create: `frontend/src/components/CategoryTree.tsx`
- Create: `frontend/src/app/categories/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/CategoryTree.tsx`**

```tsx
"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export interface CategoryNode {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  is_leaf: boolean;
  children: CategoryNode[];
}

interface Props {
  nodes: CategoryNode[];
  onAdd: (parentId: string | null) => void;
  onDelete: (id: string) => void;
  depth?: number;
}

export function CategoryTree({ nodes, onAdd, onDelete, depth = 0 }: Props) {
  return (
    <ul className={depth > 0 ? "ml-4 border-l border-gray-200 pl-3" : ""}>
      {nodes.map(node => (
        <CategoryNode key={node.id} node={node} onAdd={onAdd} onDelete={onDelete} depth={depth} />
      ))}
      <li>
        <button
          onClick={() => onAdd(depth === 0 ? null : nodes[0]?.parent_id ?? null)}
          className="text-sm text-blue-600 hover:text-blue-800 py-1"
        >
          + Добавить {depth === 0 ? "категорию" : "подкатегорию"}
        </button>
      </li>
    </ul>
  );
}

function CategoryNode({ node, onAdd, onDelete, depth }: { node: CategoryNode; onAdd: (id: string | null) => void; onDelete: (id: string) => void; depth: number }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <li className="py-1">
      <div className="flex items-center gap-2 group">
        {node.children.length > 0 && (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400 hover:text-gray-600 text-xs w-4">
            {expanded ? "▼" : "▶"}
          </button>
        )}
        {node.children.length === 0 && <span className="w-4" />}
        <span className={`text-sm ${node.is_leaf ? "text-gray-900" : "font-medium text-gray-700"}`}>{node.name}</span>
        {node.is_leaf && <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">лист</span>}
        <div className="hidden group-hover:flex items-center gap-1 ml-auto">
          <button onClick={() => onAdd(node.id)} className="text-xs text-blue-600 hover:text-blue-800">+ суб</button>
          {node.is_leaf && (
            <button onClick={() => onDelete(node.id)} className="text-xs text-red-500 hover:text-red-700">удалить</button>
          )}
        </div>
      </div>
      {expanded && node.children.length > 0 && (
        <CategoryTree nodes={node.children} onAdd={onAdd} onDelete={onDelete} depth={depth + 1} />
      )}
    </li>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/categories/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { CategoryTree, CategoryNode } from "@/components/CategoryTree";
import { apiFetch } from "@/lib/api";

export default function CategoriesPage() {
  const [tree, setTree] = useState<CategoryNode[]>([]);
  const [adding, setAdding] = useState<{ parentId: string | null } | null>(null);
  const [newName, setNewName] = useState("");

  const load = () => apiFetch<CategoryNode[]>("/categories/tree").then(setTree);
  useEffect(() => { load(); }, []);

  const handleAdd = async (parentId: string | null) => {
    setAdding({ parentId });
    setNewName("");
  };

  const submitAdd = async () => {
    if (!newName.trim()) return;
    await apiFetch("/categories", {
      method: "POST",
      body: JSON.stringify({ name: newName.trim(), parent_id: adding?.parentId }),
    });
    setAdding(null);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить категорию?")) return;
    await apiFetch(`/categories/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Категории</h1>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-xl">
        <CategoryTree nodes={tree} onAdd={handleAdd} onDelete={handleDelete} />
      </div>
      {adding !== null && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-80 space-y-3 shadow-xl">
            <h3 className="font-semibold">Новая категория</h3>
            <input
              autoFocus value={newName} onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && submitAdd()}
              placeholder="Название" className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setAdding(null)} className="text-sm text-gray-500 px-3 py-1.5 hover:bg-gray-100 rounded">Отмена</button>
              <button onClick={submitAdd} className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">Создать</button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
```

- [ ] **Step 3: Verify in browser**

Open `http://localhost:3000/categories`. Create a root category, add subcategories, verify tree renders and leaf badge appears correctly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/categories/ frontend/src/components/CategoryTree.tsx
git commit -m "feat: category tree UI — add/delete with inline modal"
```

---

## Task 10: Components UI + Enrichment Review

**Files:**
- Create: `frontend/src/components/EnrichmentBadge.tsx`
- Create: `frontend/src/app/components/page.tsx`
- Create: `frontend/src/app/components/review/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/EnrichmentBadge.tsx`**

```tsx
const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  in_review: "bg-yellow-100 text-yellow-700",
  enriched: "bg-green-100 text-green-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает",
  in_review: "На ревью",
  enriched: "Обогащён",
};

export default function EnrichmentBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.pending}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/components/page.tsx`**

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import Layout from "@/components/Layout";
import EnrichmentBadge from "@/components/EnrichmentBadge";
import { apiFetch } from "@/lib/api";

interface Component { id: string; name_internal: string; name_normalized: string | null; enrichment_status: string; category_id: string | null; }

export default function ComponentsPage() {
  const [components, setComponents] = useState<Component[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => apiFetch<Component[]>("/components").then(setComponents);
  useEffect(() => { load(); }, []);

  const handleEnrich = async (id: string) => {
    await apiFetch(`/components/${id}/enrich`, { method: "POST" });
    alert("Задача на обогащение поставлена в очередь");
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const result = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/components/import`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      body: form,
    }).then(r => r.json());
    alert(`Импортировано: ${result.imported}, пропущено: ${result.skipped}`);
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Компоненты</h1>
        <div className="flex gap-2">
          <button onClick={() => fileRef.current?.click()} className="text-sm bg-white border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50">
            Импорт CSV
          </button>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleImport} />
        </div>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Название (внутреннее)</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Нормализованное</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {components.map(c => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-900">{c.name_internal}</td>
                <td className="px-4 py-3 text-gray-500">{c.name_normalized ?? "—"}</td>
                <td className="px-4 py-3"><EnrichmentBadge status={c.enrichment_status} /></td>
                <td className="px-4 py-3 text-right">
                  {c.enrichment_status === "pending" && (
                    <button onClick={() => handleEnrich(c.id)} className="text-xs text-blue-600 hover:text-blue-800">
                      Обогатить
                    </button>
                  )}
                  {c.enrichment_status === "in_review" && (
                    <a href="/components/review" className="text-xs text-yellow-600 hover:text-yellow-800">
                      Проверить →
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
```

- [ ] **Step 3: Create `frontend/src/app/components/review/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { apiFetch } from "@/lib/api";

interface Component { id: string; name_internal: string; name_normalized: string | null; search_queries: string[]; category_id: string | null; enrichment_status: string; }
interface Category { id: string; name: string; }

export default function EnrichmentReviewPage() {
  const [components, setComponents] = useState<Component[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  const load = async () => {
    const all = await apiFetch<Component[]>("/components");
    setComponents(all.filter(c => c.enrichment_status === "in_review"));
    const tree = await apiFetch<Category[]>("/categories");
    setCategories(tree);
  };

  useEffect(() => { load(); }, []);

  const approve = async (comp: Component, categoryId: string) => {
    await apiFetch(`/components/${comp.id}`, {
      method: "PATCH",
      body: JSON.stringify({ category_id: categoryId, enrichment_status: "enriched" }),
    });
    load();
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Ревью обогащения</h1>
      {components.length === 0 && <p className="text-gray-500">Нет компонентов на ревью.</p>}
      <div className="space-y-4">
        {components.map(c => (
          <div key={c.id} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-sm text-gray-500 mb-1">Исходное: {c.name_internal}</div>
            <div className="font-medium text-gray-900 mb-2">{c.name_normalized}</div>
            {c.search_queries.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {c.search_queries.map((q, i) => (
                  <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{q}</span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
              <select
                defaultValue={c.category_id ?? ""}
                onChange={e => approve(c, e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="" disabled>Выбрать категорию...</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
              <span className="text-xs text-gray-400">Выбери категорию для подтверждения</span>
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}
```

- [ ] **Step 4: Verify in browser**

Open `http://localhost:3000/components`. Import a CSV, click "Обогатить" on a component (requires worker running), navigate to `/components/review` to confirm enrichment.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/components/ frontend/src/components/
git commit -m "feat: components UI — table, CSV import, enrichment review"
```

---

## Task 11: Supplier UI + Coverage Dashboard

**Files:**
- Create: `frontend/src/components/CoverageBar.tsx`
- Create: `frontend/src/app/suppliers/page.tsx`
- Create: `frontend/src/app/suppliers/coverage/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/CoverageBar.tsx`**

```tsx
const COLOR: Record<string, string> = {
  red: "bg-red-500",
  yellow: "bg-yellow-400",
  green: "bg-green-500",
};

export default function CoverageBar({ count, status }: { count: number; status: string }) {
  const pct = Math.min(100, (count / 6) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${COLOR[status] ?? "bg-gray-400"}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-medium min-w-[1.5rem] text-right ${status === "red" ? "text-red-600" : status === "yellow" ? "text-yellow-600" : "text-green-600"}`}>
        {count}
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/suppliers/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { apiFetch } from "@/lib/api";

interface Supplier { id: string; name: string; type: string; email: string | null; website: string | null; }

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [form, setForm] = useState({ name: "", type: "company", email: "", website: "" });
  const [adding, setAdding] = useState(false);

  const load = () => apiFetch<Supplier[]>("/suppliers").then(setSuppliers);
  useEffect(() => { load(); }, []);

  const submit = async () => {
    await apiFetch("/suppliers", { method: "POST", body: JSON.stringify(form) });
    setAdding(false);
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Поставщики</h1>
        <button onClick={() => setAdding(true)} className="text-sm bg-blue-600 text-white rounded px-3 py-1.5 hover:bg-blue-700">
          Добавить
        </button>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Название</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Тип</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Сайт</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {suppliers.map(s => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${s.type === "company" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                    {s.type === "company" ? "Компания" : "Площадка"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{s.email ?? "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {s.website ? <a href={s.website} target="_blank" className="text-blue-600 hover:underline">{s.website}</a> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {adding && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 space-y-3 shadow-xl">
            <h3 className="font-semibold">Новый поставщик</h3>
            {[
              { label: "Название", key: "name", type: "text" },
              { label: "Email", key: "email", type: "email" },
              { label: "Сайт", key: "website", type: "url" },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-sm text-gray-600 mb-1">{f.label}</label>
                <input
                  type={f.type}
                  value={(form as Record<string, string>)[f.key]}
                  onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm text-gray-600 mb-1">Тип</label>
              <select value={form.type} onChange={e => setForm(prev => ({ ...prev, type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
                <option value="company">Компания</option>
                <option value="marketplace">Площадка</option>
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setAdding(false)} className="text-sm text-gray-500 px-3 py-1.5 hover:bg-gray-100 rounded">Отмена</button>
              <button onClick={submit} className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">Создать</button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
```

- [ ] **Step 3: Create `frontend/src/app/suppliers/coverage/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import CoverageBar from "@/components/CoverageBar";
import { apiFetch } from "@/lib/api";

interface CoverageItem { category_id: string; category_name: string; supplier_count: number; status: string; }

export default function CoveragePage() {
  const [items, setItems] = useState<CoverageItem[]>([]);
  useEffect(() => { apiFetch<CoverageItem[]>("/suppliers/coverage").then(setItems); }, []);

  const red = items.filter(i => i.status === "red");
  const yellow = items.filter(i => i.status === "yellow");
  const green = items.filter(i => i.status === "green");

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Покрытие поставщиков</h1>
      {[
        { label: "Критично — нет поставщиков", items: red, color: "text-red-600" },
        { label: "Мало поставщиков (2–3)", items: yellow, color: "text-yellow-600" },
        { label: "Хорошее покрытие (4+)", items: green, color: "text-green-600" },
      ].map(group => group.items.length > 0 && (
        <div key={group.label} className="mb-6">
          <h2 className={`text-sm font-semibold uppercase tracking-wide mb-3 ${group.color}`}>{group.label}</h2>
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {group.items.map(item => (
              <div key={item.category_id} className="flex items-center gap-4 px-4 py-3">
                <span className="text-sm text-gray-900 flex-1">{item.category_name}</span>
                <div className="w-40">
                  <CoverageBar count={item.supplier_count} status={item.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </Layout>
  );
}
```

- [ ] **Step 4: Verify in browser**

Open `http://localhost:3000/suppliers` and `http://localhost:3000/suppliers/coverage`. Add a supplier, assign categories via API, verify coverage updates.

- [ ] **Step 5: Run all backend tests**

```bash
cd backend && pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Final commit for Phase 1**

```bash
git add frontend/src/app/suppliers/ frontend/src/components/CoverageBar.tsx
git commit -m "feat: supplier UI + coverage dashboard — Phase 1 complete"
```

---

## Final Verification

- [ ] `docker compose up --build` starts all services cleanly
- [ ] `http://localhost:3000` → login → dashboard shows coverage summary
- [ ] Create categories (nested), components (CSV import), suppliers (company + marketplace), assign categories
- [ ] Trigger enrichment on a component → worker processes it → review screen confirms category
- [ ] Coverage dashboard shows correct traffic-light status
- [ ] `pytest -v` — all tests pass

---

## Self-Review Checklist

- [x] Auth (login, JWT, protected routes) — Task 3 ✓
- [x] Category CRUD + hierarchical tree + leaf detection — Task 4 ✓
- [x] Component CRUD + CSV import — Task 5 ✓
- [x] Supplier CRUD (company + marketplace) + category assignment — Task 6 ✓
- [x] Coverage calculation (red/yellow/green) — Task 6 service ✓
- [x] ARQ worker + Job tracking — Task 7 ✓
- [x] OpenRouter enrichment task (normalization + search_queries + category suggestion) — Task 7 worker ✓
- [x] Enrichment review UI (approve/correct category) — Task 10 ✓
- [x] Frontend auth flow + layout — Task 8 ✓
- [x] Category tree UI — Task 9 ✓
- [x] Dashboard coverage summary — Task 8 ✓
- [x] Coverage dashboard drill-down — Task 11 ✓
- [x] Docker Compose deployment — Task 1 ✓
- [x] All critical paths have tests ✓
