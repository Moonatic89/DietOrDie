from datetime import date
from typing import Optional, Tuple
from app.models import UserProfile
from app.schemas import HealthMetricsResponse

def calculate_bmi(weight_kg: float, height_cm: float) -> Tuple[float, str]:
    if not height_cm or height_cm <= 0 or not weight_kg or weight_kg <= 0:
        return 0.0, "Non disponibile"
    
    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)
    
    if bmi < 18.5:
        category = "Sottopeso"
    elif bmi < 25.0:
        category = "Normopeso"
    elif bmi < 30.0:
        category = "Sovrappeso"
    elif bmi < 35.0:
        category = "Obesità di classe I"
    elif bmi < 40.0:
        category = "Obesità di classe II"
    else:
        category = "Obesità di classe III"
        
    return bmi, category

def calculate_age(birth_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str = "male") -> float:
    # Formula di Mifflin-St Jeor
    base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
    if gender.lower() == "female":
        return round(base - 161.0, 1)
    else:
        return round(base + 5.0, 1)

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,      # Poco o nessun esercizio
    "light": 1.375,        # Esercizio leggero 1-3 volte a settimana
    "moderate": 1.55,      # Esercizio moderato 3-5 volte a settimana
    "active": 1.725,       # Esercizio pesante 6-7 volte a settimana
    "very_active": 1.9     # Lavoro fisico pesante o allenamenti doppi
}

def calculate_tdee(bmr: float, activity_level: str = "sedentary") -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.2)
    return round(bmr * multiplier, 1)

def get_user_health_metrics(profile: Optional[UserProfile]) -> HealthMetricsResponse:
    if not profile or not profile.current_weight_kg or not profile.height_cm:
        return HealthMetricsResponse()

    weight = profile.current_weight_kg
    height = profile.height_cm
    bmi, category = calculate_bmi(weight, height)

    age = calculate_age(profile.birth_date) or 30
    bmr = calculate_bmr(weight, height, age, profile.gender or "male")
    tdee = calculate_tdee(bmr, profile.activity_level or "sedentary")

    recommended = int(tdee)
    diff = None
    if profile.target_weight_kg:
        diff = round(profile.target_weight_kg - weight, 1)
        if diff < -0.5:
            # Deficit sano
            recommended = max(1200, int(tdee - 450))
        elif diff > 0.5:
            # Surplus controllato
            recommended = int(tdee + 300)

    return HealthMetricsResponse(
        bmi=bmi,
        bmi_category=category,
        bmr=bmr,
        tdee=tdee,
        recommended_calories=recommended,
        weight_diff_kg=diff
    )

def calculate_ride_calories(
    duration_seconds: int,
    distance_km: float,
    avg_speed_kmh: float,
    profile: Optional[UserProfile],
    resistance_level: int = 1,
    heart_rate_avg: Optional[int] = None
) -> float:
    """
    Calcola le calorie bruciate durante una sessione di cyclette basandosi su
    modelli biomeccanici reali di potenza meccanica (Watts) e rendimento metabolico umano (~23%).
    Evita le sovrastime tipiche del modello MET generico per pesi corporei elevati su attrezzi a sella.
    """
    weight = profile.current_weight_kg if profile and profile.current_weight_kg else 75.0
    height = profile.height_cm if profile and profile.height_cm else 175.0
    age = calculate_age(profile.birth_date) if profile else 30
    age = age or 30
    gender = profile.gender if profile and profile.gender else "male"

    hours = duration_seconds / 3600.0
    if hours <= 0:
        return 0.0

    # 1. Se è disponibile la frequenza cardiaca: Formula di Keytel (gold standard HR)
    if heart_rate_avg and heart_rate_avg > 50:
        if gender.lower() == "female":
            cal_per_min = (-20.4022 + (0.4472 * heart_rate_avg) - (0.1263 * weight) + (0.074 * age)) / 4.184
        else:
            cal_per_min = (-55.0969 + (0.6309 * heart_rate_avg) + (0.1988 * weight) + (0.2017 * age)) / 4.184
        return max(1.0, round(cal_per_min * (duration_seconds / 60.0), 1))

    # 2. Modello di potenza meccanica per cyclette magnetica (Watts)
    # A 15 km/h: ~67W base; a 18 km/h: ~78W base; a 22 km/h: ~94W base
    clamped_speed = max(3.0, min(45.0, avg_speed_kmh))
    base_watts = 10.0 + 3.8 * clamped_speed

    # Resistenza magnetica (livelli 1 a 8):
    # Livello 1: 0.75x (freno aperto); Livello 8: 1.39x (freno chiuso, carico sostenuto)
    clamped_res = max(1, min(8, resistance_level))
    res_factor = 0.75 + (clamped_res - 1) * 0.0914  # da 0.75 (liv. 1) a 1.39 (liv. 8)
    mech_watts = base_watts * res_factor

    # Spesa metabolica da potenza meccanica:
    # 1 Watt-ora meccanico richiede circa 3.65 kcal di spesa metabolica (efficienza ~23.5%)
    power_kcal_per_hour = mech_watts * 3.65

    # Quota metabolica basale e lavoro posturale orario (BMR / 24)
    bmr = calculate_bmr(weight, height, age, gender)
    bmr_per_hour = bmr / 24.0

    # Dispendio orario complessivo
    total_kcal_per_hour = power_kcal_per_hour + bmr_per_hour
    calories = total_kcal_per_hour * hours

    return round(max(1.0, calories), 1)

def calculate_journey_calories(distance_km: float, profile: Optional[UserProfile]) -> int:
    """Calcola le calorie realistiche stimate per percorrere una determinata distanza sulla cyclette"""
    weight = profile.current_weight_kg if profile and profile.current_weight_kg else 75.0
    # Consumo medio realistico su cyclette: ~18-28 kcal per km in base al peso
    kcal_per_km = 16.0 + max(0.0, (weight - 60.0)) * 0.12
    return int(round(distance_km * kcal_per_km))
