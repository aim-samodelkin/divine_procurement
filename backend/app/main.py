from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.components.router import router as components_router
from app.jobs.router import router as jobs_router
from app.public_suppliers.router import router as public_suppliers_router
from app.supplier_candidates import models as _supplier_candidate_models  # noqa: F401
from app.supplier_candidates.router import router as supplier_candidates_router
from app.suppliers.router import router as suppliers_router

app = FastAPI(title="Procurement Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(components_router)
app.include_router(suppliers_router)
app.include_router(supplier_candidates_router)
app.include_router(public_suppliers_router)
app.include_router(jobs_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
