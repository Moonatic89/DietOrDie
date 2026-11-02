from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Journey, UserJourneyProgress
from app.schemas import (
    JourneyResponse,
    UserJourneyProgressResponse
)
from app.auth import get_current_user
from app.services.gamification import (
    seed_default_journeys,
    get_or_create_user_progress,
    format_progress_response
)

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.get("", response_model=List[JourneyResponse])
def get_all_journeys(db: Session = Depends(get_db)):
    seed_default_journeys(db)
    journeys = db.query(Journey).all()
    resp = []
    for j in journeys:
        j_resp = JourneyResponse.model_validate(j)
        j_resp.estimated_calories_total = int(round(j.total_distance_km * 70.0 * 0.38))
        resp.append(j_resp)
    return resp


@router.get("/active", response_model=UserJourneyProgressResponse)
def get_active_journey(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    seed_default_journeys(db)

    progress = db.query(UserJourneyProgress).filter(
        UserJourneyProgress.user_id == current_user.id,
        UserJourneyProgress.is_active == True
    ).first()

    if not progress:
        # Attiva il primo per default
        default_j = db.query(Journey).filter(Journey.slug == "lord-of-the-rings").first()
        if not default_j:
            default_j = db.query(Journey).first()
        if not default_j:
            raise HTTPException(status_code=404, detail="Nessun percorso disponibile")
        progress = get_or_create_user_progress(db, current_user.id, default_j.id)

    return format_progress_response(progress, db)


@router.post("/{journey_id}/activate", response_model=UserJourneyProgressResponse)
def activate_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Percorso non trovato")

    # Disattiva altri percorsi
    db.query(UserJourneyProgress).filter(
        UserJourneyProgress.user_id == current_user.id
    ).update({"is_active": False})

    progress = get_or_create_user_progress(db, current_user.id, journey_id)
    progress.is_active = True
    db.commit()
    db.refresh(progress)

    return format_progress_response(progress, db)
