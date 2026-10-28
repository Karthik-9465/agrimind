import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db.init_db import init_db
from app.modules.auth.router import router as auth_router
from app.modules.farm.router import router as farm_router
from app.modules.agent.router import router as agent_router
from app.modules.notifications.router import router as notifications_router
from app.scheduler import start_scheduler, shutdown_scheduler

load_dotenv()

app = FastAPI(
    title="Agrimind Agentic — Farm AI Assistant API",
    description="Backend modular monolith for crop diagnosis, irrigation/fertilizer rules, weather, and farm management.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto initialize database tables & background scheduler
@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()

# Routers
app.include_router(auth_router)
app.include_router(farm_router)
app.include_router(agent_router)
app.include_router(notifications_router)

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Agrimind Agentic API",
        "version": "1.0.0"
    }

@app.get("/api/v1/health/gemini", tags=["Health"])
def gemini_health_check():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return {
            "status": "warning",
            "gemini_configured": False,
            "message": "GEMINI_API_KEY environment variable is not configured with a valid key. Explicit DEMO / MOCK mode active for disease tools."
        }
    
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Respond with 'Agrimind System Ready' in 3 words."
        )
        return {
            "status": "healthy",
            "gemini_configured": True,
            "response": response.text.strip()
        }
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "400" in error_msg:
            return {
                "status": "warning",
                "gemini_configured": False,
                "message": "Provided GEMINI_API_KEY is invalid. Please update .env with a valid Google AI Studio API key (starts with AIzaSy...). Explicit DEMO / MOCK mode is active.",
                "error": error_msg
            }
        return {
            "status": "configured_with_error",
            "gemini_configured": True,
            "error": error_msg
        }
