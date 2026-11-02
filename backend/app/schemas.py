from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

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
