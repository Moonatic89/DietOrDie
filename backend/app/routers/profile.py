from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserProfile, WeightLog
from app.schemas import UserProfileUpdate, UserProfileResponse, WeightLogCreate, WeightLogResponse, HealthMetricsResponse
from app.auth import get_current_user
from app.services.metrics import get_user_health_metrics

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("", response_model=UserProfileResponse)
def update_profile(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    old_weight = profile.current_weight_kg

    for field, val in profile_in.model_dump(exclude_unset=True).items():
        setattr(profile, field, val)

    # Se il peso è cambiato, crea automaticamente un log nella cronologia peso
    if profile_in.current_weight_kg and profile_in.current_weight_kg != old_weight:
        weight_entry = WeightLog(
            user_id=current_user.id,
            weight_kg=profile_in.current_weight_kg,
            recorded_at=date.today(),
            notes="Aggiornamento peso profilo"
        )
        db.add(weight_entry)

    db.commit()
    db.refresh(profile)
    return profile

@router.get("/metrics", response_model=HealthMetricsResponse)
def get_metrics(current_user: User = Depends(get_current_user)):
    return get_user_health_metrics(current_user.profile)

@router.get("/weight-history", response_model=List[WeightLogResponse])
def get_weight_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(WeightLog).filter(
        WeightLog.user_id == current_user.id
    ).order_by(WeightLog.recorded_at.asc()).all()
    return logs

@router.post("/weight-log", response_model=WeightLogResponse)
def add_weight_log(
    log_in: WeightLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log_date = log_in.recorded_at or date.today()
    log = WeightLog(
        user_id=current_user.id,
        weight_kg=log_in.weight_kg,
        recorded_at=log_date,
        notes=log_in.notes
    )
    db.add(log)

    # Aggiorna anche il profilo corrente se è la data odierna o recente
    if current_user.profile:
        current_user.profile.current_weight_kg = log_in.weight_kg

    db.commit()
    db.refresh(log)
    return log
