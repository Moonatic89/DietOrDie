from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.gamification import seed_default_journeys
from app.services.mqtt_service import mqtt_service
from app.routers import auth, profile, nutrition, rides, journeys, websocket

# Crea le tabelle nel database
Base.metadata.create_all(bind=engine)

# Inizializza i percorsi di default
with SessionLocal() as db:
    seed_default_journeys(db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Avvia listener MQTT in background
    loop = asyncio.get_running_loop()
    mqtt_service.start(loop)
    yield
    # Arresta listener MQTT
    mqtt_service.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Personal Fitness & Nutrition Tracker with AI Vision and Gamified Cyclette Expeditions",
    lifespan=lifespan
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory per foto pasti e display
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(profile.router, prefix=settings.API_V1_PREFIX)
app.include_router(nutrition.router, prefix=settings.API_V1_PREFIX)
app.include_router(rides.router, prefix=settings.API_V1_PREFIX)
app.include_router(journeys.router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

# Se la build del frontend è presente in dist/ o ../frontend/dist, servila come SPA
frontend_dist = Path(__file__).resolve().parent.parent / "dist"
if not frontend_dist.exists():
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
