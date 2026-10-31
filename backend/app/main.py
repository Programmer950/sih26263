"""FastAPI Main Application Factory."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.institutions import router as institutions_router
from app.api.v1.students import router as students_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.discrepancies import router as discrepancies_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.verification import router as verification_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.audit import router as audit_router



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apaar_setu")

app = FastAPI(
    title="APAAR SETU — API",
    description="Longitudinal Student Data Integrity & Verification Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler for consistent error envelope
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": str(exc) if settings.DEBUG else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": "apaar-setu",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Mount API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(institutions_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(submissions_router, prefix="/api/v1")
app.include_router(snapshots_router, prefix="/api/v1")
app.include_router(reconciliation_router, prefix="/api/v1")
app.include_router(discrepancies_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


