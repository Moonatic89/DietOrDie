from datetime import datetime, timedelta
import uuid
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import User, RideSession, UserJourneyProgress
from app.schemas import (
    RideSessionCreate,
    RideSessionResponse,
    RideLogResultResponse,
    AIAnalyzeDisplayResponse
)
from app.auth import get_current_user
from app.services.gamification import record_ride_progress, format_progress_response
from app.services.vision import analyze_display_image
from app.services.metrics import calculate_ride_calories

router = APIRouter(prefix="/rides", tags=["rides"])

UPLOAD_RIDES_DIR = settings.UPLOAD_DIR / "rides"
UPLOAD_RIDES_DIR.mkdir(parents=True, exist_ok=True)


class ESP32Payload(BaseModel):
    api_key: Optional[str] = None
    username: Optional[str] = None
    session_uid: Optional[str] = None
    duration_seconds: int
    distance_km: float
    current_speed_kmh: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    rpm: Optional[float] = None
    pulses: Optional[int] = None
    calories_burned: Optional[float] = None
    resistance_level: Optional[int] = 1
    heart_rate_avg: Optional[int] = None
    is_finished: Optional[bool] = False
    notes: Optional[str] = "Sessione registrata via ESP32 Wi-Fi"


@router.get("", response_model=List[RideSessionResponse])
def get_rides(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rides = db.query(RideSession).filter(
        RideSession.user_id == current_user.id
    ).order_by(RideSession.created_at.desc()).limit(limit).all()
    return rides


@router.post("", response_model=RideLogResultResponse)
def log_ride(
    ride_in: RideSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    duration_sec = ride_in.duration_seconds
    dist_km = ride_in.distance_km

    if duration_sec <= 0 or dist_km <= 0:
        raise HTTPException(status_code=400, detail="Durata e distanza devono essere maggiori di zero")

    hours = duration_sec / 3600.0
    avg_speed = ride_in.avg_speed_kmh
    if not avg_speed or avg_speed <= 0:
        avg_speed = round(dist_km / hours, 1)

    cal_burned = ride_in.calories_burned
    if not cal_burned or cal_burned <= 0:
        cal_burned = calculate_ride_calories(
            duration_seconds=duration_sec,
            distance_km=dist_km,
            avg_speed_kmh=avg_speed,
            profile=current_user.profile,
            resistance_level=ride_in.resistance_level or 1,
            heart_rate_avg=ride_in.heart_rate_avg
        )

    ride = RideSession(
        user_id=current_user.id,
        journey_id=ride_in.journey_id,
        duration_seconds=duration_sec,
        distance_km=dist_km,
        avg_speed_kmh=avg_speed,
        calories_burned=cal_burned,
        resistance_level=ride_in.resistance_level or 1,
        heart_rate_avg=ride_in.heart_rate_avg,
        photo_path=ride_in.photo_path,
        notes=ride_in.notes
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)

    progress, celebration = record_ride_progress(
        db=db,
        user_id=current_user.id,
        distance_km=dist_km,
        journey_id=ride_in.journey_id
    )

    return RideLogResultResponse(
        ride=ride,
        progress=progress,
        newly_unlocked_milestone=celebration
    )


@router.get("/active", response_model=Optional[RideSessionResponse])
def get_active_ride(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restituisce l'eventuale sessione in corso (dati ricevuti via telemetria negli ultimi 15 secondi)"""
    cutoff = datetime.utcnow() - timedelta(seconds=15)
    ride = db.query(RideSession).filter(
        RideSession.user_id == current_user.id,
        RideSession.updated_at >= cutoff
    ).order_by(RideSession.updated_at.desc()).first()
    return ride


@router.post("/esp32", response_model=RideLogResultResponse)
def log_esp32_ride(
    payload: ESP32Payload,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint dedicato per la telemetria continua Wi-Fi dall'ESP32 (intervallo raccomandato: 5 secondi).
    Aggrega automaticamente i tick streaming in una singola sessione pulita nel database senza spammare record.
    """
    provided_key = payload.api_key or x_api_key
    if provided_key != settings.ESP32_API_KEY:
        raise HTTPException(status_code=403, detail="ESP32 API Key non valida")

    # Identifica l'utente target
    user = None
    if payload.username:
        user = db.query(User).filter(User.username == payload.username).first()

    if not user:
        # Fallback al primo utente registrato
        user = db.query(User).first()

    if not user:
        raise HTTPException(status_code=404, detail="Nessun utente trovato sul sistema")

    duration_sec = payload.duration_seconds
    dist_km = payload.distance_km

    if duration_sec <= 0 or dist_km <= 0:
        raise HTTPException(status_code=400, detail="Dati non validi: durata e distanza devono essere > 0")

    hours = duration_sec / 3600.0
    avg_speed = payload.avg_speed_kmh or round(dist_km / hours, 1)

    cal_burned = payload.calories_burned
    if not cal_burned or cal_burned <= 0:
        cal_burned = calculate_ride_calories(
            duration_seconds=duration_sec,
            distance_km=dist_km,
            avg_speed_kmh=avg_speed,
            profile=user.profile,
            resistance_level=payload.resistance_level or 1,
            heart_rate_avg=payload.heart_rate_avg
        )

    # 1. Verifica se esiste già una sessione attiva da aggiornare (ultimi 60s o stesso session_uid)
    active_ride = None
    cutoff_time = datetime.utcnow() - timedelta(seconds=60)
    session_uid = payload.session_uid

    if session_uid:
        active_ride = db.query(RideSession).filter(
            RideSession.user_id == user.id,
            RideSession.session_uid == session_uid
        ).first()
    else:
        # Cerca sessioni streaming ESP32 recenti entro gli ultimi 60 secondi
        latest_ride = db.query(RideSession).filter(
            RideSession.user_id == user.id,
            RideSession.session_uid.isnot(None),
            RideSession.updated_at >= cutoff_time
        ).order_by(RideSession.updated_at.desc()).first()

        if latest_ride:
            active_ride = latest_ride

    if active_ride and not payload.is_finished:
        # Calcola delta distanza per il percorso RPG
        delta_dist = max(0.0, round(dist_km - active_ride.distance_km, 3))

        active_ride.duration_seconds = duration_sec
        active_ride.distance_km = dist_km
        active_ride.avg_speed_kmh = avg_speed
        if payload.current_speed_kmh is not None:
            active_ride.current_speed_kmh = payload.current_speed_kmh
        if payload.rpm is not None:
            active_ride.rpm = payload.rpm
        if payload.resistance_level:
            active_ride.resistance_level = payload.resistance_level
        if payload.heart_rate_avg:
            active_ride.heart_rate_avg = payload.heart_rate_avg
        active_ride.calories_burned = cal_burned
        active_ride.updated_at = datetime.utcnow()
        if session_uid and not active_ride.session_uid:
            active_ride.session_uid = session_uid

        db.commit()
        db.refresh(active_ride)

        progress = None
        celebration = None
        if delta_dist > 0:
            progress, celebration = record_ride_progress(
                db=db,
                user_id=user.id,
                distance_km=delta_dist
            )
        else:
            prog = db.query(UserJourneyProgress).filter(
                UserJourneyProgress.user_id == user.id,
                UserJourneyProgress.is_active == True
            ).first()
            if prog:
                progress = format_progress_response(prog, db)

        return RideLogResultResponse(
            ride=active_ride,
            progress=progress,
            newly_unlocked_milestone=celebration
        )

    # 2. Se non esiste una sessione attiva negli ultimi 60s, crea una NUOVA sessione
    generated_uid = session_uid or f"esp32_{user.id}_{int(datetime.utcnow().timestamp())}"
    ride = RideSession(
        user_id=user.id,
        session_uid=generated_uid,
        duration_seconds=duration_sec,
        distance_km=dist_km,
        avg_speed_kmh=avg_speed,
        current_speed_kmh=payload.current_speed_kmh,
        rpm=payload.rpm,
        calories_burned=cal_burned,
        resistance_level=payload.resistance_level or 1,
        heart_rate_avg=payload.heart_rate_avg,
        notes=payload.notes or "Ricevuto da ESP32",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)

    progress, celebration = record_ride_progress(
        db=db,
        user_id=user.id,
        distance_km=dist_km
    )

    return RideLogResultResponse(
        ride=ride,
        progress=progress,
        newly_unlocked_milestone=celebration
    )


@router.post("/analyze-display", response_model=AIAnalyzeDisplayResponse)
async def analyze_display(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    ext = Path(file.filename or "display.jpg").suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato immagine non supportato")

    content = await file.read()
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_RIDES_DIR / filename

    with open(dest_path, "wb") as f:
        f.write(content)

    mime = file.content_type or "image/jpeg"
    analysis = await analyze_display_image(content, mime)
    analysis.image_url = f"/uploads/rides/{filename}"
    return analysis
