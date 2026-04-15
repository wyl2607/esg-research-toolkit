"""ESG Research Toolkit — FastAPI main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from benchmark.api import router as benchmark_router
from core.database import init_db
from core.limiter import limiter
from esg_frameworks.api import router as frameworks_router
from report_parser.api import router as report_router
from taxonomy_scorer.api import router as taxonomy_router
from techno_economics.api import router as techno_router

app = FastAPI(
    title="ESG Research Toolkit",
    description="Open-source toolkit for corporate ESG report analysis, EU Taxonomy compliance scoring, and renewable energy techno-economic analysis (LCOE/NPV/IRR).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(report_router)
app.include_router(taxonomy_router)
app.include_router(techno_router)
app.include_router(frameworks_router)
app.include_router(benchmark_router)


@app.get("/")
def root() -> dict[str, str | list[str]]:
    return {
        "name": "ESG Research Toolkit",
        "version": "0.1.0",
        "modules": ["report_parser", "taxonomy_scorer", "techno_economics", "esg_frameworks", "benchmark"],
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
