"""AYURVEDA_AGENT FastAPI Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.settings import get_settings
from core.database import init_database
from core.exceptions import ClinicalGovernanceException
from api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager initializing persistent database and caches."""
    settings = get_settings()
    init_database(settings.database_path)
    yield


settings = get_settings()

app = FastAPI(
    title="AYURVEDA_AGENT — Autonomous Clinical AYUSH HIS & CDSS",
    description=(
        "Enterprise-grade, zero-trust, mathematically grounded Hospital Information System (HIS), "
        "Electronic Health Record (EHR), and Clinical Decision Support System (CDSS) for Ayurvedic Hospitals."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Standard Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ClinicalGovernanceException)
async def clinical_governance_exception_handler(request: Request, exc: ClinicalGovernanceException):
    """Intercept clinical governance and safety exceptions with standardized JSON structure."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "legal_status": "DRAFT_AYUSH_DECISION_SUPPORT_REQUIRES_PHYSICIAN_SIGNATURE"
        }
    )


@app.get("/", tags=["System Root"])
def root():
    """System Identity and Statutory Compliance Metadata."""
    return {
        "system": "AYURVEDA_AGENT",
        "version": settings.app_version,
        "compliance": [
            "NCISM Act 2020",
            "Drugs & Cosmetics Act 1940 (Schedule E1 & T)",
            "NABH AYUSH Accreditation Standards (2nd Edition, 2023)"
        ],
        "ontologies": [
            "NAMASTE Portal",
            "WHO ICD-11 Traditional Medicine Module 1 (TM1)",
            "SNOMED CT"
        ],
        "status": "OPERATIONAL",
        "api_v1_health": "/api/v1/health",
        "api_docs": "/docs"
    }


app.include_router(api_v1_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
