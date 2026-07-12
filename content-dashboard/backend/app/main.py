import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, SessionLocal, engine
from .api import auth_routes, config, contents, ideas, kpi, metrics, sources, users
from .seed import run_seed
from .services.scheduler import start_scheduler
from .settings import CORS_ORIGINS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    stop_scheduler = start_scheduler()
    yield
    stop_scheduler.set()


app = FastAPI(title="Mailift Content Dashboard API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth_routes, users, ideas, contents, metrics, kpi, sources, config):
    app.include_router(module.router)
