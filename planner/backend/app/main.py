"""Mailift Planner — backend FastAPI.

Avvio dev:
    uvicorn app.main:app --port 8001 --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .api import brands, catalog, integrations, plans, system, templates

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mailift Planner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(brands.router)
app.include_router(catalog.router)
app.include_router(integrations.router)
app.include_router(templates.router)
app.include_router(plans.router)
