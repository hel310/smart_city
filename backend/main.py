"""
Smart City Platform — FastAPI Backend
Neo-Sousse 2030

Run with:
    uvicorn backend.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .db import ping
from .routers.capteurs import router as capteurs_router
from .routers.interventions import router as interventions_router
from .routers.compiler import router as compiler_router
from .routers.ai_routes import router as ai_router
from .routers.data import (
    mesures_router, zones_router,
    citoyens_router, vehicules_router, trajets_router,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart City API — Neo-Sousse 2030",
    description=(
        "Backend REST pour la plateforme Smart City.\n\n"
        "**Modules :** Capteurs · Interventions · Mesures · "
        "Compilateur NL→SQL · IA Générative · Automates FSM"
    ),
    version="1.0.0",
)

# Allow the React frontend (Vite) and Streamlit to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(capteurs_router)
app.include_router(interventions_router)
app.include_router(mesures_router)
app.include_router(zones_router)
app.include_router(citoyens_router)
app.include_router(vehicules_router)
app.include_router(trajets_router)
app.include_router(compiler_router)
app.include_router(ai_router)

# ── Health / root ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Smart City API",
        "version": "1.0.0",
        "status": "ok",
    }


@app.get("/health", tags=["Health"])
def health():
    try:
        db_version = ping()
        return {"status": "ok", "database": db_version}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
