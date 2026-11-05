from datetime import datetime, timedelta
import uuid
import json
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
    RideMergeRequest,
    RidePerformanceResponse,
    AIAnalyzeDisplayResponse
)
from app.auth import get_current_user
from app.services.gamification import record_ride_progress, format_progress_response
from app.services.vision import analyze_display_image
from app.services.metrics import (
    calculate_ride_calories,
    calculate_mechanical_watts,
    append_telemetry_tick,
    generate_ride_performance
)
from app.routers.websocket import ws_manager

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

    total_pedals = ride_in.total_pedal_strokes or int(round((dist_km * 1000.0) / 3.50))

    ride = RideSession(
        user_id=current_user.id,
        journey_id=ride_in.journey_id,
        duration_seconds=duration_sec,
        distance_km=dist_km,
        avg_speed_kmh=avg_speed,
        calories_burned=cal_burned,
        resistance_level=ride_in.resistance_level or 1,
        heart_rate_avg=ride_in.heart_rate_avg,
        total_pedal_strokes=total_pedals,
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
    ).order_by(RideSession.updated_at.desc(), RideSession.id.desc()).first()
    return ride


@router.post("/esp32", response_model=RideLogResultResponse)
async def log_esp32_ride(
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

    pulses = payload.pulses
    total_pedals = pulses if pulses is not None else int(round((dist_km * 1000.0) / 3.50))

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
        active_ride.total_pedal_strokes = total_pedals
        if payload.resistance_level:
            active_ride.resistance_level = payload.resistance_level
        if payload.heart_rate_avg:
            active_ride.heart_rate_avg = payload.heart_rate_avg
        active_ride.calories_burned = cal_burned
        active_ride.telemetry_history_json = append_telemetry_tick(
            existing_json=active_ride.telemetry_history_json,
            sec=duration_sec,
            speed=payload.current_speed_kmh or avg_speed,
            rpm=payload.rpm or 0.0,
            km=dist_km,
            resistance=payload.resistance_level or 1
        )
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

        res = RideLogResultResponse(
            ride=active_ride,
            progress=progress,
            newly_unlocked_milestone=celebration
        )

        try:
            ws_payload = {
                "type": "ride_tick",
                "ride": {
                    "id": active_ride.id,
                    "user_id": active_ride.user_id,
                    "username": user.username,
                    "duration_seconds": active_ride.duration_seconds,
                    "distance_km": active_ride.distance_km,
                    "avg_speed_kmh": active_ride.avg_speed_kmh,
                    "current_speed_kmh": active_ride.current_speed_kmh,
                    "rpm": active_ride.rpm,
                    "total_pedal_strokes": active_ride.total_pedal_strokes,
                    "pulses": active_ride.total_pedal_strokes,
                    "calories_burned": active_ride.calories_burned,
                    "resistance_level": active_ride.resistance_level
                },
                "progress": progress.model_dump() if progress else None,
                "celebration": celebration.model_dump() if celebration else None
            }
            await ws_manager.broadcast(ws_payload)
        except Exception:
            pass

        return res

    # 2. Se non esiste una sessione attiva negli ultimi 60s, crea una NUOVA sessione
    generated_uid = session_uid or f"esp32_{user.id}_{int(datetime.utcnow().timestamp())}"
    initial_history = append_telemetry_tick(
        existing_json=None,
        sec=duration_sec,
        speed=payload.current_speed_kmh or avg_speed,
        rpm=payload.rpm or 0.0,
        km=dist_km,
        resistance=payload.resistance_level or 1
    )
    ride = RideSession(
        user_id=user.id,
        session_uid=generated_uid,
        duration_seconds=duration_sec,
        distance_km=dist_km,
        avg_speed_kmh=avg_speed,
        current_speed_kmh=payload.current_speed_kmh,
        rpm=payload.rpm,
        total_pedal_strokes=total_pedals,
        telemetry_history_json=initial_history,
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

    res = RideLogResultResponse(
        ride=ride,
        progress=progress,
        newly_unlocked_milestone=celebration
    )

    try:
        ws_payload = {
            "type": "ride_tick",
            "ride": {
                "id": ride.id,
                "user_id": ride.user_id,
                "username": user.username,
                "duration_seconds": ride.duration_seconds,
                "distance_km": ride.distance_km,
                "avg_speed_kmh": ride.avg_speed_kmh,
                "current_speed_kmh": ride.current_speed_kmh,
                "rpm": ride.rpm,
                "total_pedal_strokes": ride.total_pedal_strokes,
                "pulses": ride.total_pedal_strokes,
                "calories_burned": ride.calories_burned,
                "resistance_level": ride.resistance_level
            },
            "progress": progress.model_dump() if progress else None,
            "celebration": celebration.model_dump() if celebration else None
        }
        await ws_manager.broadcast(ws_payload)
    except Exception:
        pass

    return res


@router.post("/merge", response_model=RideSessionResponse)
def merge_rides(
    payload: RideMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unisce due o più sessioni di cyclette in un'unica sessione continua.
    Ideale per recuperare la continuità quando l'ESP32 o il chip Arduino si riavvia per interruzione di alimentazione.
    """
    if len(payload.ride_ids) < 2:
        raise HTTPException(status_code=400, detail="Seleziona almeno 2 sessioni da unire")

    rides = db.query(RideSession).filter(
        RideSession.id.in_(payload.ride_ids),
        RideSession.user_id == current_user.id
    ).order_by(RideSession.created_at.asc()).all()

    if len(rides) < 2:
        raise HTTPException(status_code=404, detail="Sessioni selezionate non trovate o non appartenenti all'utente")

    primary_ride = rides[0]
    other_rides = rides[1:]

    total_duration = sum(r.duration_seconds for r in rides)
    total_distance = round(sum(r.distance_km for r in rides), 3)
    total_pedals = sum(
        (r.total_pedal_strokes if r.total_pedal_strokes is not None else int(round((r.distance_km * 1000.0) / 3.50)))
        for r in rides
    )

    hours = total_duration / 3600.0 if total_duration > 0 else 0.0
    avg_speed = round(total_distance / hours, 1) if hours > 0 else 0.0

    dur_with_rpm = sum(r.duration_seconds for r in rides if (r.rpm or 0) > 0)
    if dur_with_rpm > 0:
        avg_rpm = round(sum((r.rpm or 0.0) * r.duration_seconds for r in rides if (r.rpm or 0) > 0) / dur_with_rpm, 1)
    else:
        avg_rpm = round((total_pedals / (total_duration / 60.0)), 1) if total_duration > 0 else 0.0

    avg_res = round(sum((r.resistance_level or 1) * r.duration_seconds for r in rides) / total_duration) if total_duration > 0 else 1
    avg_res = max(1, min(8, avg_res))

    total_calories = calculate_ride_calories(
        duration_seconds=total_duration,
        distance_km=total_distance,
        avg_speed_kmh=avg_speed,
        profile=current_user.profile,
        resistance_level=avg_res
    )

    merged_history = []
    time_offset = 0
    distance_offset = 0.0

    for r in rides:
        r_points = []
        if r.telemetry_history_json:
            try:
                r_points = json.loads(r.telemetry_history_json)
            except Exception:
                r_points = []
        if not r_points:
            r_points = [
                {
                    "sec": 0,
                    "speed": r.avg_speed_kmh or 0.0,
                    "rpm": r.rpm or 0.0,
                    "km": 0.0,
                    "watts": calculate_mechanical_watts(r.avg_speed_kmh or 0.0, r.resistance_level or 1)
                },
                {
                    "sec": r.duration_seconds,
                    "speed": r.avg_speed_kmh or 0.0,
                    "rpm": r.rpm or 0.0,
                    "km": r.distance_km,
                    "watts": calculate_mechanical_watts(r.avg_speed_kmh or 0.0, r.resistance_level or 1)
                }
            ]

        for pt in r_points:
            new_pt = dict(pt)
            new_pt["sec"] = int(pt.get("sec", 0)) + time_offset
            new_pt["km"] = round(float(pt.get("km", 0.0)) + distance_offset, 3)
            merged_history.append(new_pt)

        time_offset += r.duration_seconds
        distance_offset += r.distance_km

    if len(merged_history) > 250:
        stride = len(merged_history) / 250.0
        sampled = [merged_history[int(i * stride)] for i in range(249)]
        sampled.append(merged_history[-1])
        merged_history = sampled

    primary_ride.duration_seconds = total_duration
    primary_ride.distance_km = total_distance
    primary_ride.avg_speed_kmh = avg_speed
    primary_ride.current_speed_kmh = 0.0
    primary_ride.rpm = avg_rpm
    primary_ride.resistance_level = avg_res
    primary_ride.total_pedal_strokes = total_pedals
    primary_ride.calories_burned = total_calories
    primary_ride.telemetry_history_json = json.dumps(merged_history)
    merged_ids_str = ", ".join(str(r.id) for r in rides)
    existing_notes = (primary_ride.notes or "").split(" [Unite sessioni")[0]
    primary_ride.notes = f"{existing_notes} [Unite sessioni #{merged_ids_str}]".strip()
    primary_ride.updated_at = datetime.utcnow()

    for other in other_rides:
        db.delete(other)

    db.commit()
    db.refresh(primary_ride)
    return primary_ride


@router.get("/{ride_id}/performance", response_model=RidePerformanceResponse)
def get_ride_performance(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restituisce le metriche prestazionali avanzate, zone cardio e splits per il grafico"""
    ride = db.query(RideSession).filter(
        RideSession.id == ride_id,
        RideSession.user_id == current_user.id
    ).first()

    if not ride:
        raise HTTPException(status_code=404, detail="Sessione di pedalata non trovata")

    return generate_ride_performance(ride)


@router.delete("/{ride_id}")
def delete_ride(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Elimina una sessione di pedalata e adegua il progresso percorso attivo se applicabile"""
    ride = db.query(RideSession).filter(
        RideSession.id == ride_id,
        RideSession.user_id == current_user.id
    ).first()

    if not ride:
        raise HTTPException(status_code=404, detail="Sessione non trovata")

    prog = db.query(UserJourneyProgress).filter(
        UserJourneyProgress.user_id == current_user.id,
        UserJourneyProgress.is_active == True
    ).first()
    if prog and ride.distance_km:
        prog.cumulative_distance_km = max(0.0, round(prog.cumulative_distance_km - ride.distance_km, 3))

    db.delete(ride)
    db.commit()
    return {"status": "success", "message": "Sessione eliminata con successo"}


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
