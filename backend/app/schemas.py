from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator

# --- AUTH & USER ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: Optional[str] = None

# --- PROFILE & HEALTH METRICS ---
class UserProfileBase(BaseModel):
    birth_date: Optional[date] = None
    gender: str = "male"
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    activity_level: str = "sedentary"
    daily_calorie_target: Optional[int] = 2000
    notes: Optional[str] = None

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    updated_at: Optional[datetime] = None

class HealthMetricsResponse(BaseModel):
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    recommended_calories: Optional[int] = None
    weight_diff_kg: Optional[float] = None

class WeightLogCreate(BaseModel):
    weight_kg: float
    recorded_at: Optional[date] = None
    notes: Optional[str] = None

class WeightLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    weight_kg: float
    recorded_at: date
    notes: Optional[str] = None
    created_at: datetime

# --- BODY COMPOSITION (SMART SCALE / BIOIMPEDANCE) ---
class BodyCompositionBase(BaseModel):
    recorded_at: Optional[date] = None
    weight_kg: float
    bmi: Optional[float] = None
    body_fat_pct: Optional[float] = None
    subcutaneous_fat_pct: Optional[float] = None
    visceral_fat: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    skeletal_muscle_pct: Optional[float] = None
    bone_mass_kg: Optional[float] = None
    fat_free_mass_kg: Optional[float] = None
    metabolic_age: Optional[int] = None
    bmr_kcal: Optional[float] = None
    body_water_pct: Optional[float] = None
    protein_pct: Optional[float] = None
    notes: Optional[str] = None

class BodyCompositionCreate(BodyCompositionBase):
    @model_validator(mode="before")
    @classmethod
    def normalize_keys_and_values(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        
        alias_map = {
            "peso": "weight_kg",
            "peso_kg": "weight_kg",
            "weight": "weight_kg",
            "grasso": "body_fat_pct",
            "grasso_corporeo": "body_fat_pct",
            "percentuale_grasso_corporeo": "body_fat_pct",
            "body_fat": "body_fat_pct",
            "percentuale_di_grasso_corporeo": "body_fat_pct",
            "grasso_sottocutaneo": "subcutaneous_fat_pct",
            "subcutaneous_fat": "subcutaneous_fat_pct",
            "grasso_viscerale": "visceral_fat",
            "viscerale": "visceral_fat",
            "visceral_fat": "visceral_fat",
            "massa_muscolare": "muscle_mass_kg",
            "muscolo": "muscle_mass_kg",
            "muscle_mass": "muscle_mass_kg",
            "percentuale_muscolo_scheletrica": "skeletal_muscle_pct",
            "percentuale_muscoloscheletrica": "skeletal_muscle_pct",
            "muscolo_scheletrico": "skeletal_muscle_pct",
            "skeletal_muscle": "skeletal_muscle_pct",
            "massa_ossea": "bone_mass_kg",
            "ossa": "bone_mass_kg",
            "bone_mass": "bone_mass_kg",
            "peso_senza_grassi": "fat_free_mass_kg",
            "peso_corporeo_senza_grassi": "fat_free_mass_kg",
            "massa_magra": "fat_free_mass_kg",
            "fat_free_mass": "fat_free_mass_kg",
            "ffm": "fat_free_mass_kg",
            "eta_metabolica": "metabolic_age",
            "età_metabolica": "metabolic_age",
            "metabolic_age": "metabolic_age",
            "bmr": "bmr_kcal",
            "bmr_kcal": "bmr_kcal",
            "metabolismo_basale": "bmr_kcal",
            "acqua": "body_water_pct",
            "acqua_corporea": "body_water_pct",
            "percentuale_acqua": "body_water_pct",
            "percentuale_di_acqua_corporea": "body_water_pct",
            "body_water": "body_water_pct",
            "proteine": "protein_pct",
            "percentuale_proteica": "protein_pct",
            "protein": "protein_pct",
            "data": "recorded_at",
            "date": "recorded_at",
            "note": "notes"
        }
        
        normalized = {}
        for k, v in data.items():
            key_clean = str(k).strip().lower().replace(" ", "_").replace("-", "_")
            target_key = alias_map.get(key_clean, key_clean)
            
            if isinstance(v, str):
                v_clean = v.strip().replace("kg", "").replace("%", "").replace("kcal", "").strip()
                v_clean = v_clean.replace(",", ".")
                if target_key in ["metabolic_age"]:
                    try:
                        v = int(float(v_clean))
                    except (ValueError, TypeError):
                        pass
                elif target_key in ["bmr_kcal"]:
                    try:
                        v = float(v_clean)
                    except (ValueError, TypeError):
                        pass
                elif target_key not in ["recorded_at", "notes"]:
                    try:
                        v = float(v_clean)
                    except (ValueError, TypeError):
                        pass
            normalized[target_key] = v
        return normalized

class BodyCompositionBulkInput(BaseModel):
    recorded_at: Optional[date] = None
    raw_json: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class BodyCompositionDelta(BaseModel):
    days: Optional[int] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_pct: Optional[float] = None
    subcutaneous_fat_pct: Optional[float] = None
    visceral_fat: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    skeletal_muscle_pct: Optional[float] = None
    bone_mass_kg: Optional[float] = None
    fat_free_mass_kg: Optional[float] = None
    body_water_pct: Optional[float] = None
    protein_pct: Optional[float] = None

class BodyCompositionResponse(BodyCompositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    recorded_at: date
    created_at: datetime
    delta: Optional[BodyCompositionDelta] = None

class AIProgressReviewResponse(BaseModel):
    review_markdown: str
    overall_trend: str
    key_metrics_summary: Dict[str, Any] = {}
    recommendations: List[str] = []

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    profile: Optional[UserProfileResponse] = None
    metrics: Optional[HealthMetricsResponse] = None

# --- NUTRITION ---
class FoodItemBase(BaseModel):
    name: str
    portion_g: Optional[float] = None
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0

class FoodItemCreate(FoodItemBase):
    pass

class FoodItemResponse(FoodItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_entry_id: int

class MealEntryCreate(BaseModel):
    meal_type: str = "pranzo"  # colazione, pranzo, cena, spuntino
    date: Optional[date] = None
    title: str = "Pasto"
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    notes: Optional[str] = None
    image_path: Optional[str] = None
    items: List[FoodItemCreate] = []

class MealEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_type: str
    date: date
    title: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    image_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    items: List[FoodItemResponse] = []

class DailyNutritionSummary(BaseModel):
    date: date
    target_calories: int
    consumed_calories: float
    burned_calories: float
    net_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    meals: List[MealEntryResponse] = []

class AIFoodItem(BaseModel):
    name: str
    portion_g: Optional[float] = None
    calories: float
    protein: float
    carbs: float
    fat: float

class AIAnalyzeFoodResponse(BaseModel):
    dish_name: str
    estimated_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence_notes: str
    suggested_items: List[AIFoodItem] = []
    image_url: Optional[str] = None

# --- RIDES & GAMIFICATION ---
class RideSessionCreate(BaseModel):
    duration_seconds: int
    distance_km: float
    avg_speed_kmh: Optional[float] = None
    calories_burned: Optional[float] = None
    resistance_level: Optional[int] = 1
    heart_rate_avg: Optional[int] = None
    notes: Optional[str] = None
    photo_path: Optional[str] = None
    journey_id: Optional[int] = None

class RideSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    journey_id: Optional[int] = None
    session_uid: Optional[str] = None
    duration_seconds: int
    distance_km: float
    avg_speed_kmh: float
    current_speed_kmh: Optional[float] = None
    rpm: Optional[float] = None
    calories_burned: float
    resistance_level: Optional[int] = 1
    heart_rate_avg: Optional[int] = None
    notes: Optional[str] = None
    photo_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class AIAnalyzeDisplayResponse(BaseModel):
    distance_km: Optional[float] = None
    duration_seconds: Optional[int] = None
    avg_speed_kmh: Optional[float] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None

class JourneyMilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_index: int
    name: str
    distance_km: float
    estimated_calories: Optional[int] = None
    description: Optional[str] = None
    lore_text: Optional[str] = None
    image_url: Optional[str] = None
    badge_icon: str
    is_unlocked: bool = False

class JourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: Optional[str] = None
    universe: str
    total_distance_km: float
    estimated_calories_total: Optional[int] = None
    cover_image: Optional[str] = None
    badge_icon: str
    milestones: List[JourneyMilestoneResponse] = []

class UserJourneyProgressResponse(BaseModel):
    id: int
    journey: JourneyResponse
    cumulative_distance_km: float
    remaining_distance_km: float
    progress_percentage: float
    estimated_calories_total: int = 0
    estimated_calories_remaining: int = 0
    is_active: bool
    is_completed: bool
    current_milestone: Optional[JourneyMilestoneResponse] = None
    next_milestone: Optional[JourneyMilestoneResponse] = None
    distance_to_next_km: Optional[float] = None
    unlocked_milestones_count: int = 0
    total_milestones_count: int = 0

class MilestoneUnlockCelebration(BaseModel):
    milestone_name: str
    distance_km: float
    lore_text: Optional[str] = None
    badge_icon: str
    journey_title: str

class RideLogResultResponse(BaseModel):
    ride: RideSessionResponse
    progress: Optional[UserJourneyProgressResponse] = None
    newly_unlocked_milestone: Optional[MilestoneUnlockCelebration] = None
