import app.config  # Centralized environment & settings initialization
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db
from app.db.mongodb import get_mongodb
from app.modules.auth.router import router as auth_router
from app.modules.farm.router import router as farm_router
from app.modules.agent.router import router as agent_router
from app.modules.notifications.router import router as notifications_router
from app.modules.agent.tools.disease import check_gemini_status
from app.modules.agent.voice_service import GnaniVoiceService
from app.scheduler import start_scheduler, shutdown_scheduler

logger = logging.getLogger("agrimind.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables, MongoDB probe, and start background scheduler
    logger.info("Starting AgriMind Agentic Platform...")
    init_db()
    get_mongodb()
    start_scheduler()
    yield
    # Shutdown: Cleanly terminate background scheduler
    logger.info("Shutting down AgriMind Agentic Platform...")
    shutdown_scheduler()

app = FastAPI(
    title="AgriMind AI — Agentic Smart Agriculture Assistant API",
    description="Full-stack AI assistant powering crop disease diagnosis (Gemini Vision), smart irrigation (FAO-56), fertilizer prescriptions (ICAR STCR), live weather, APMC Mandi prices, and regional voice interaction (Gnani AI).",
    version="2.0.0",
    lifespan=lifespan
)

# Production CORS configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Modular Routers
app.include_router(auth_router)
app.include_router(farm_router)
app.include_router(agent_router)
app.include_router(notifications_router)

@app.get("/api/v1/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "AgriMind AI Platform API",
        "version": "2.0.0",
        "engines": {
            "disease_vision": "Google Gemini 2.5 Flash",
            "voice_stt_tts": "Gnani AI Prisma v3.0 & Timbre v3.0",
            "irrigation": "FAO-56 Penman-Monteith",
            "fertilizer": "ICAR STCR Rule Engine",
            "weather": "Open-Meteo & OpenWeatherMap",
            "market": "Official APMC Agmarknet Benchmark"
        }
    }

@app.get("/api/v1/health/integrations", tags=["Health"])
@app.get("/api/health/integrations", tags=["Health"])
def integrations_health_check(refresh: bool = Query(False, description="Force live connectivity re-test")):
    """
    Comprehensive health and mode status of all external AI and agronomic providers.
    Supports ?refresh=true to force instant API re-probing.
    """
    gemini_stat = check_gemini_status(force_probe=refresh)
    gnani_stat = GnaniVoiceService.check_gnani_status()

    return {
        "status": "healthy",
        "service": "AgriMind AI Platform",
        "version": "2.0.0",
        "providers": {
            "gemini_vision": gemini_stat,
            "gnani_ai": gnani_stat,
            "weather": {
                "mode": "LIVE",
                "provider": "Open-Meteo & OpenWeatherMap",
                "status": "operational"
            },
            "market": {
                "mode": "OPERATIONAL",
                "provider": "APMC Mandi Dataset (Agmarknet Aligned)",
                "commodities_count": 8
            },
            "irrigation_engine": {
                "mode": "OPERATIONAL",
                "standard": "FAO-56 Penman-Monteith (ETc = ETo * Kc)"
            },
            "fertilizer_engine": {
                "mode": "OPERATIONAL",
                "standard": "ICAR Soil Test Crop Response (STCR)"
            }
        }
    }

@app.get("/api/v1/health/gemini", tags=["Health"])
def gemini_health_check(refresh: bool = Query(False, description="Force live connectivity re-test")):
    return check_gemini_status(force_probe=refresh)

@app.get("/api/v1/health/gnani", tags=["Health"])
def gnani_health_check():
    return GnaniVoiceService.check_gnani_status()

@app.get("/api/v1/health/mongodb", tags=["Health"])
def mongodb_health_check():
    db = get_mongodb()
    if db is None:
        return {
            "status": "unconfigured",
            "mongodb_configured": False,
            "message": "MONGODB_URI not configured. Operating with primary SQLAlchemy relational storage."
        }
    return {
        "status": "connected",
        "mongodb_configured": True,
        "message": "Connected to MongoDB Atlas database."
    }
