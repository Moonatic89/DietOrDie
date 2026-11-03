import json
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserProfile, WeightLog, BodyCompositionLog
from app.schemas import (
    UserProfileUpdate, UserProfileResponse,
    WeightLogCreate, WeightLogResponse,
    HealthMetricsResponse,
    BodyCompositionCreate, BodyCompositionBulkInput,
    BodyCompositionResponse, BodyCompositionDelta,
    AIProgressReviewResponse
)
from app.auth import get_current_user
from app.services.metrics import get_user_health_metrics
from app.services.progress_ai import analyze_body_composition_progress

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


# --- BODY COMPOSITION (SMART SCALE) ---

def build_composition_responses(logs: List[BodyCompositionLog]) -> List[BodyCompositionResponse]:
    """Costruisce le risposte con il delta rispetto alla pesata precedente (più vecchia)"""
    results: List[BodyCompositionResponse] = []
    for i, log in enumerate(logs):
        delta = None
        if i + 1 < len(logs):
            prev = logs[i + 1]
            days = (log.recorded_at - prev.recorded_at).days
            delta = BodyCompositionDelta(
                days=days,
                weight_kg=round(log.weight_kg - prev.weight_kg, 2) if log.weight_kg is not None and prev.weight_kg is not None else None,
                bmi=round(log.bmi - prev.bmi, 2) if log.bmi is not None and prev.bmi is not None else None,
                body_fat_pct=round(log.body_fat_pct - prev.body_fat_pct, 1) if log.body_fat_pct is not None and prev.body_fat_pct is not None else None,
                subcutaneous_fat_pct=round(log.subcutaneous_fat_pct - prev.subcutaneous_fat_pct, 1) if log.subcutaneous_fat_pct is not None and prev.subcutaneous_fat_pct is not None else None,
                visceral_fat=round(log.visceral_fat - prev.visceral_fat, 1) if log.visceral_fat is not None and prev.visceral_fat is not None else None,
                muscle_mass_kg=round(log.muscle_mass_kg - prev.muscle_mass_kg, 2) if log.muscle_mass_kg is not None and prev.muscle_mass_kg is not None else None,
                skeletal_muscle_pct=round(log.skeletal_muscle_pct - prev.skeletal_muscle_pct, 1) if log.skeletal_muscle_pct is not None and prev.skeletal_muscle_pct is not None else None,
                bone_mass_kg=round(log.bone_mass_kg - prev.bone_mass_kg, 2) if log.bone_mass_kg is not None and prev.bone_mass_kg is not None else None,
                fat_free_mass_kg=round(log.fat_free_mass_kg - prev.fat_free_mass_kg, 2) if log.fat_free_mass_kg is not None and prev.fat_free_mass_kg is not None else None,
                body_water_pct=round(log.body_water_pct - prev.body_water_pct, 1) if log.body_water_pct is not None and prev.body_water_pct is not None else None,
                protein_pct=round(log.protein_pct - prev.protein_pct, 1) if log.protein_pct is not None and prev.protein_pct is not None else None,
            )
        resp = BodyCompositionResponse.model_validate(log)
        resp.delta = delta
        results.append(resp)
    return results


def _save_body_composition_log(
    db: Session,
    user: User,
    data: BodyCompositionCreate
) -> BodyCompositionLog:
    log_date = data.recorded_at or date.today()
    log = BodyCompositionLog(
        user_id=user.id,
        recorded_at=log_date,
        weight_kg=data.weight_kg,
        bmi=data.bmi,
        body_fat_pct=data.body_fat_pct,
        subcutaneous_fat_pct=data.subcutaneous_fat_pct,
        visceral_fat=data.visceral_fat,
        muscle_mass_kg=data.muscle_mass_kg,
        skeletal_muscle_pct=data.skeletal_muscle_pct,
        bone_mass_kg=data.bone_mass_kg,
        fat_free_mass_kg=data.fat_free_mass_kg,
        metabolic_age=data.metabolic_age,
        bmr_kcal=data.bmr_kcal,
        body_water_pct=data.body_water_pct,
        protein_pct=data.protein_pct,
        notes=data.notes,
    )
    db.add(log)

    # Aggiorna peso profilo se è la misurazione più recente
    latest_date = db.query(BodyCompositionLog.recorded_at).filter(
        BodyCompositionLog.user_id == user.id
    ).order_by(BodyCompositionLog.recorded_at.desc()).first()

    if not latest_date or log_date >= latest_date[0]:
        if user.profile:
            user.profile.current_weight_kg = data.weight_kg
        # Aggiunge anche WeightLog per il grafico standard
        w_log = WeightLog(
            user_id=user.id,
            weight_kg=data.weight_kg,
            recorded_at=log_date,
            notes="Pesata bilancia smart"
        )
        db.add(w_log)

    db.commit()
    db.refresh(log)
    return log


@router.get("/body-composition", response_model=List[BodyCompositionResponse])
def get_body_composition_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(BodyCompositionLog).filter(
        BodyCompositionLog.user_id == current_user.id
    ).order_by(BodyCompositionLog.recorded_at.desc(), BodyCompositionLog.id.desc()).all()
    return build_composition_responses(logs)


@router.post("/body-composition", response_model=BodyCompositionResponse)
def add_body_composition(
    log_in: BodyCompositionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log = _save_body_composition_log(db, current_user, log_in)
    all_logs = db.query(BodyCompositionLog).filter(
        BodyCompositionLog.user_id == current_user.id
    ).order_by(BodyCompositionLog.recorded_at.desc(), BodyCompositionLog.id.desc()).all()
    responses = build_composition_responses(all_logs)
    for r in responses:
        if r.id == log.id:
            return r
    return BodyCompositionResponse.model_validate(log)


@router.post("/body-composition/bulk-json", response_model=BodyCompositionResponse)
def add_body_composition_bulk(
    bulk_in: BodyCompositionBulkInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payload = {}
    if bulk_in.raw_json:
        try:
            payload = json.loads(bulk_in.raw_json)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato JSON non valido: {str(e)}"
            )
    elif bulk_in.data:
        payload = dict(bulk_in.data)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fornire 'raw_json' oppure l'oggetto 'data'"
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il JSON fornito deve essere un oggetto chiave-valore con i dati della bilancia"
        )

    if bulk_in.recorded_at:
        payload["recorded_at"] = bulk_in.recorded_at

    try:
        validated_data = BodyCompositionCreate.model_validate(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Errore nei dati della bilancia (campo peso obbligatorio): {str(e)}"
        )

    log = _save_body_composition_log(db, current_user, validated_data)
    all_logs = db.query(BodyCompositionLog).filter(
        BodyCompositionLog.user_id == current_user.id
    ).order_by(BodyCompositionLog.recorded_at.desc(), BodyCompositionLog.id.desc()).all()
    responses = build_composition_responses(all_logs)
    for r in responses:
        if r.id == log.id:
            return r
    return BodyCompositionResponse.model_validate(log)


@router.get("/body-composition/ai-review", response_model=AIProgressReviewResponse)
async def get_body_composition_ai_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(BodyCompositionLog).filter(
        BodyCompositionLog.user_id == current_user.id
    ).order_by(BodyCompositionLog.recorded_at.desc(), BodyCompositionLog.id.desc()).all()

    profile = current_user.profile
    return await analyze_body_composition_progress(logs, profile)


@router.delete("/body-composition/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_body_composition_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log = db.query(BodyCompositionLog).filter(
        BodyCompositionLog.id == log_id,
        BodyCompositionLog.user_id == current_user.id
    ).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Misurazione non trovata")

    db.delete(log)
    db.commit()
    return None

