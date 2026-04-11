"""ESG Research Toolkit — FastAPI main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from report_parser.api import router as report_router
from techno_economics.api import router as techno_router
from taxonomy_scorer.api import router as taxonomy_router

app = FastAPI(
    title="ESG Research Toolkit",
    description="Open-source toolkit for corporate ESG report analysis, EU Taxonomy compliance scoring, and renewable energy techno-economic analysis (LCOE/NPV/IRR).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(report_router)
app.include_router(techno_router)
app.include_router(taxonomy_router)


@app.get("/")
def root():
    return {
        "name": "ESG Research Toolkit",
        "version": "0.1.0",
        "modules": ["report_parser", "taxonomy_scorer", "techno_economics"],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
