import uuid
import json
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.config import settings
from app.models import User, MealEntry, FoodItem, RideSession
from app.schemas import (
    MealEntryCreate,
    MealEntryResponse,
    DailyNutritionSummary,
    AIAnalyzeFoodResponse
)
from app.auth import get_current_user
from app.services.vision import analyze_food_image

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

UPLOAD_MEALS_DIR = settings.UPLOAD_DIR / "meals"
UPLOAD_MEALS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/summary/{date_str}", response_model=DailyNutritionSummary)
def get_daily_summary(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido (usa YYYY-MM-DD)")

    meals = db.query(MealEntry).filter(
        MealEntry.user_id == current_user.id,
        MealEntry.date == target_date
    ).all()

    # Calcola calorie bruciate con la cyclette nello stesso giorno
    rides = db.query(RideSession).filter(
        RideSession.user_id == current_user.id,
        RideSession.created_at >= f"{date_str} 00:00:00",
        RideSession.created_at <= f"{date_str} 23:59:59"
    ).all()

    burned_cal = sum(r.calories_burned for r in rides)
    consumed_cal = sum(m.total_calories for m in meals)
    tot_protein = sum(m.total_protein for m in meals)
    tot_carbs = sum(m.total_carbs for m in meals)
    tot_fat = sum(m.total_fat for m in meals)

    target_cal = current_user.profile.daily_calorie_target if current_user.profile else 2000

    return DailyNutritionSummary(
        date=target_date,
        target_calories=target_cal,
        consumed_calories=round(consumed_cal, 1),
        burned_calories=round(burned_cal, 1),
        net_calories=round(consumed_cal - burned_cal, 1),
        total_protein=round(tot_protein, 1),
        total_carbs=round(tot_carbs, 1),
        total_fat=round(tot_fat, 1),
        meals=meals
    )


@router.post("/meals", response_model=MealEntryResponse)
def create_meal(
    meal_in: MealEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    meal_date = meal_in.date or date.today()

    meal = MealEntry(
        user_id=current_user.id,
        meal_type=meal_in.meal_type,
        date=meal_date,
        title=meal_in.title,
        total_calories=meal_in.total_calories,
        total_protein=meal_in.total_protein,
        total_carbs=meal_in.total_carbs,
        total_fat=meal_in.total_fat,
        notes=meal_in.notes,
        image_path=meal_in.image_path
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)

    # Aggiungi singoli elementi se presenti
    for item in meal_in.items:
        food_item = FoodItem(
            meal_entry_id=meal.id,
            name=item.name,
            portion_g=item.portion_g,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat
        )
        db.add(food_item)

    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/meals/{meal_id}")
def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    meal = db.query(MealEntry).filter(
        MealEntry.id == meal_id,
        MealEntry.user_id == current_user.id
    ).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Pasto non trovato")

    db.delete(meal)
    db.commit()
    return {"status": "success", "message": "Pasto eliminato"}


@router.post("/analyze-photo", response_model=AIAnalyzeFoodResponse)
async def analyze_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Validazione estensione
    ext = Path(file.filename or "dish.jpg").suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato immagine non supportato (usa JPG, PNG o WEBP)")

    content = await file.read()
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_MEALS_DIR / filename

    with open(dest_path, "wb") as f:
        f.write(content)

    mime = file.content_type or "image/jpeg"
    analysis = await analyze_food_image(content, mime)
    analysis.image_url = f"/uploads/meals/{filename}"
    return analysis
