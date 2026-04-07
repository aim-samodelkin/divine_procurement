from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.components.router import router as components_router
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


@app.get("/health")
async def health():
    return {"status": "ok"}
