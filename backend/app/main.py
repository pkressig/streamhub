from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api.routes import sources, health, benchmarks, rankings
import app.models  # noqa: register all models with SQLAlchemy

app = FastAPI(
    title="PascalHub API",
    description="Source Intelligence Platform — v0.2",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(benchmarks.router, prefix="/api/benchmarks", tags=["benchmarks"])
app.include_router(rankings.router, prefix="/api/rankings", tags=["rankings"])
