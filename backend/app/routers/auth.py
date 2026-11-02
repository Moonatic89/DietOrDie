from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserProfile
from app.schemas import UserRegister, UserResponse, Token, UserLogin, HealthMetricsResponse
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.metrics import get_user_health_metrics
from app.services.gamification import seed_default_journeys, get_or_create_user_progress, Journey

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Controlla se username esiste già
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Questo nome utente è già registrato"
        )

    # Crea utente
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name or user_in.username,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Crea profilo utente vuoto
    profile = UserProfile(
        user_id=user.id,
        gender="male",
        height_cm=175.0,
        current_weight_kg=75.0,
        target_weight_kg=70.0,
        activity_level="sedentary",
        daily_calorie_target=2000
    )
    db.add(profile)
    db.commit()

    # Assicurati che i percorsi esistano e attiva il primo per l'utente
    seed_default_journeys(db)
    lotr = db.query(Journey).filter(Journey.slug == "lord-of-the-rings").first()
    if lotr:
        get_or_create_user_progress(db, user.id, lotr.id)

    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome utente o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

@router.post("/login-json", response_model=Token)
def login_json(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome utente o password errati",
        )
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    metrics = get_user_health_metrics(current_user.profile)
    resp = UserResponse.model_validate(current_user)
    resp.metrics = metrics
    return resp

@router.get("/users-list")
def list_system_users(db: Session = Depends(get_db)):
    """Restituisce la lista degli utenti registrati per facilitare il cambio rapido profilo"""
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "full_name": u.full_name} for u in users]
