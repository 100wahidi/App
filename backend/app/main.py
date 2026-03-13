"""Application FastAPI principale pour le reporting data quality."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from .routers.reporting_routes import router as reporting_router


# Configuration de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Startup
    print("🚀 Démarrage de l'API Data Quality")
    print(f"⏰ {datetime.now()}")
    yield
    # Shutdown
    print("🛑 Arrêt de l'API Data Quality")


# Création de l'application FastAPI
app = FastAPI(
    title="Data Quality API",
    description="""
    ## API de Reporting Data Quality

    Cette API génère des rapports de qualité des données via les règles
    définies dans `scripts.py` (KPI, consistency, accuracy, dead KRI, évolution).

    ### 📊 Fonctionnalités
    - Upload et analyse de fichiers CSV/Excel
    - KPIs globaux et par colonne
    - Détection d'anomalies de cohérence
    - Alertes KRI inactifs
    - Distribution et évolution mensuelle des KRI
    """,
    version="1.0.0",
    contact={
        "name": "Équipe Data Quality",
        "email": "data-quality@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)

# Configuration CORS pour le frontend React
origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Gestion globale des exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Erreur interne du serveur",
            "details": str(exc),
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


# Routes principales
@app.get("/", tags=["Root"])
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "🔍 API Data Quality Reporting",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health"
    }


@app.get("/info", tags=["Root"])
async def api_info():
    """Informations détaillées sur l'API"""
    return {
        "name": "Data Quality API",
        "description": "API de reporting de qualité des données basée sur scripts.py",
        "version": "1.0.0",
        "features": [
            "Upload et analyse de fichiers CSV/Excel",
            "KPIs globaux et par colonne",
            "Consistency check",
            "Accuracy check avec référentiel",
            "Dead KRI alerts et distribution temporelle"
        ],
        "engine": "scripts.py",
        "supported_formats": ["CSV", "Excel (.xlsx, .xls)"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Vérification simple de santé de l'API."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


# Inclusion des routes
app.include_router(reporting_router)


# Configuration pour le développement
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )