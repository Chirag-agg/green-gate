"""
GreenGate Backend — FastAPI Application Entry Point.
AI + Blockchain CBAM Carbon Compliance Platform for Indian MSME Exporters.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import engine, Base
from routers import auth, calculator, reports, verify, products

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _ensure_carbon_report_schema_compatibility() -> None:
    """Add newly introduced carbon_reports columns for existing SQLite databases."""
    required_columns = {
        "expected_energy": "REAL",
        "deviation_ratio": "REAL",
        "credibility_score": "REAL",
        "verification_status": "VARCHAR",
        "machinery_score": "REAL",
        "regional_energy_score": "REAL",
        "temporal_score": "REAL",
        "scope3_emissions": "REAL",
        "scope3_breakdown": "TEXT",
        "estimated_emissions": "REAL",
        "twin_consistency_score": "REAL",
        "confidence_score": "REAL",
        "requires_evidence": "BOOLEAN",
        "evidence_files": "TEXT",
        "verification_notes": "TEXT",
    }

    with engine.begin() as connection:
        table_info = connection.exec_driver_sql("PRAGMA table_info(carbon_reports)").fetchall()
        existing_columns = {row[1] for row in table_info}

        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            connection.exec_driver_sql(
                f"ALTER TABLE carbon_reports ADD COLUMN {column_name} {column_type}"
            )
            logger.info("✅ Added missing column carbon_reports.%s", column_name)


def _ensure_product_schema_compatibility() -> None:
    """Add newly introduced product/supply-chain columns for existing SQLite databases."""
    products_required_columns = {
        "created_by": "VARCHAR",
    }
    nodes_required_columns = {
        "company_name": "VARCHAR",
        "discovered_source": "VARCHAR",
        "confidence_score": "REAL",
    }

    with engine.begin() as connection:
        products_info = connection.exec_driver_sql("PRAGMA table_info(products)").fetchall()
        products_existing = {row[1] for row in products_info}
        for column_name, column_type in products_required_columns.items():
            if column_name in products_existing:
                continue
            connection.exec_driver_sql(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}")
            logger.info("✅ Added missing column products.%s", column_name)

        nodes_info = connection.exec_driver_sql("PRAGMA table_info(supply_chain_nodes)").fetchall()
        nodes_existing = {row[1] for row in nodes_info}
        for column_name, column_type in nodes_required_columns.items():
            if column_name in nodes_existing:
                continue
            connection.exec_driver_sql(f"ALTER TABLE supply_chain_nodes ADD COLUMN {column_name} {column_type}")
            logger.info("✅ Added missing column supply_chain_nodes.%s", column_name)


def _get_cors_origins() -> list[str]:
    """Resolve CORS origins from environment, with strict production defaults."""
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    cors_env = os.getenv("CORS_ORIGINS", "").strip()

    if cors_env:
        origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    else:
        origins = []

    if environment in {"production", "prod"}:
        if not origins:
            raise RuntimeError(
                "CORS_ORIGINS is required in production. Set comma-separated allowed origins in backend/.env"
            )
        return origins

    if origins:
        return origins

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    _ensure_carbon_report_schema_compatibility()
    _ensure_product_schema_compatibility()
    logger.info("✅ Database tables created / verified")
    logger.info("🚀 GreenGate backend is running!")
    yield
    logger.info("👋 GreenGate backend shutting down")


app = FastAPI(
    title="GreenGate API",
    description=(
        "AI + Blockchain CBAM Carbon Compliance Platform for Indian MSME Exporters. "
        "Calculate carbon emissions, get AI-powered reduction recommendations, "
        "and certify reports on the Polygon blockchain."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins = _get_cors_origins()
logger.info("CORS origins configured: %s", cors_origins)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(calculator.router)
app.include_router(reports.router)
app.include_router(verify.router)
app.include_router(products.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "GreenGate API",
        "version": "1.0.0",
        "blockchain_rpc_configured": bool(os.getenv("POLYGON_RPC_URL")),
        "contract_address_configured": bool(os.getenv("CONTRACT_ADDRESS")),
    }
