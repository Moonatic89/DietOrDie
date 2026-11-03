from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    weight_logs = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan", order_by="desc(WeightLog.recorded_at)")
    body_compositions = relationship("BodyCompositionLog", back_populates="user", cascade="all, delete-orphan", order_by="desc(BodyCompositionLog.recorded_at)")
    meals = relationship("MealEntry", back_populates="user", cascade="all, delete-orphan", order_by="desc(MealEntry.created_at)")
    rides = relationship("RideSession", back_populates="user", cascade="all, delete-orphan", order_by="desc(RideSession.created_at)")
    journey_progress = relationship("UserJourneyProgress", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(10), default="male")  # male, female, other
    height_cm = Column(Float, nullable=True)
    current_weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    activity_level = Column(String(20), default="sedentary")  # sedentary, light, moderate, active, very_active
    daily_calorie_target = Column(Integer, default=2000)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    recorded_at = Column(Date, default=date.today, nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weight_logs")


class BodyCompositionLog(Base):
    __tablename__ = "body_composition_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recorded_at = Column(Date, default=date.today, nullable=False, index=True)
    
    # 13 Parametri della bilancia bioimpedenziometrica
    weight_kg = Column(Float, nullable=False)
    bmi = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    subcutaneous_fat_pct = Column(Float, nullable=True)
    visceral_fat = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    skeletal_muscle_pct = Column(Float, nullable=True)
    bone_mass_kg = Column(Float, nullable=True)
    fat_free_mass_kg = Column(Float, nullable=True)
    metabolic_age = Column(Integer, nullable=True)
    bmr_kcal = Column(Float, nullable=True)
    body_water_pct = Column(Float, nullable=True)
    protein_pct = Column(Float, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="body_compositions")


class MealEntry(Base):
    __tablename__ = "meal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meal_type = Column(String(20), default="pranzo")  # colazione, pranzo, cena, spuntino
    date = Column(Date, default=date.today, nullable=False)
    title = Column(String(120), nullable=False, default="Pasto")
    total_calories = Column(Float, default=0.0)
    total_protein = Column(Float, default=0.0)
    total_carbs = Column(Float, default=0.0)
    total_fat = Column(Float, default=0.0)
    image_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    ai_analysis_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meals")
    items = relationship("FoodItem", back_populates="meal", cascade="all, delete-orphan")


class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_entry_id = Column(Integer, ForeignKey("meal_entries.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    portion_g = Column(Float, nullable=True)
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)

    meal = relationship("MealEntry", back_populates="items")


class Journey(Base):
    __tablename__ = "journeys"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    universe = Column(String(50), nullable=False)  # es: "Il Signore degli Anelli", "Elden Ring"
    total_distance_km = Column(Float, nullable=False)
    cover_image = Column(String(255), nullable=True)
    badge_icon = Column(String(50), default="compass")

    milestones = relationship("JourneyMilestone", back_populates="journey", cascade="all, delete-orphan", order_by="JourneyMilestone.order_index")


class JourneyMilestone(Base):
    __tablename__ = "journey_milestones"

    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)
    distance_km = Column(Float, nullable=False)  # Km cumulativi richiesti per sbloccare la tappa
    description = Column(Text, nullable=True)
    lore_text = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    badge_icon = Column(String(50), default="map-pin")

    journey = relationship("Journey", back_populates="milestones")


class UserJourneyProgress(Base):
    __tablename__ = "user_journey_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    journey_id = Column(Integer, ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False)
    cumulative_distance_km = Column(Float, default=0.0)
    current_milestone_id = Column(Integer, ForeignKey("journey_milestones.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="journey_progress")
    journey = relationship("Journey")
    current_milestone = relationship("JourneyMilestone")


class RideSession(Base):
    __tablename__ = "ride_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    journey_id = Column(Integer, ForeignKey("journeys.id", ondelete="SET NULL"), nullable=True)
    session_uid = Column(String(64), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=False)  # durata in secondi
    distance_km = Column(Float, nullable=False)         # distanza percorsa in km
    avg_speed_kmh = Column(Float, nullable=False)       # velocità media km/h
    current_speed_kmh = Column(Float, nullable=True)    # velocità istantanea km/h
    rpm = Column(Float, nullable=True)                  # cadenza pedalate al minuto
    calories_burned = Column(Float, default=0.0)        # stima calorie bruciate
    resistance_level = Column(Integer, default=1)       # livello resistenza cyclette (1-8)
    heart_rate_avg = Column(Integer, nullable=True)
    photo_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="rides")
    journey = relationship("Journey")
