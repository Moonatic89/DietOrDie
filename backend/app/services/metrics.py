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
    Calcola le calorie bruciate durante una sessione di cyclette considerando:
    - Peso (kg), Altezza (cm), Età (anni), Sesso e BMI dell'utente
    - Durata e velocità media
    - Livello di resistenza della cyclette (da 1 a 8)
    - Frequenza cardiaca media (Formula scientifica Keytel, se rilevata)
    """
    weight = profile.current_weight_kg if profile and profile.current_weight_kg else 70.0
    height = profile.height_cm if profile and profile.height_cm else 175.0
    age = calculate_age(profile.birth_date) if profile else 30
    age = age or 30
    gender = profile.gender if profile and profile.gender else "male"
    bmi, _ = calculate_bmi(weight, height)

    hours = duration_seconds / 3600.0
    if hours <= 0:
        return 0.0

    # 1. Se è disponibile la frequenza cardiaca: Formula di Keytel (gold standard)
    if heart_rate_avg and heart_rate_avg > 50:
        if gender.lower() == "female":
            cal_per_min = (-20.4022 + (0.4472 * heart_rate_avg) - (0.1263 * weight) + (0.074 * age)) / 4.184
        else:
            cal_per_min = (-55.0969 + (0.6309 * heart_rate_avg) + (0.1988 * weight) + (0.2017 * age)) / 4.184
        return max(1.0, round(cal_per_min * (duration_seconds / 60.0), 1))

    # 2. Modello metabolico ACSM con correzione per resistenza (1-8), velocità e BMI
    if avg_speed_kmh < 15.0:
        base_met = 4.8
    elif avg_speed_kmh < 20.0:
        base_met = 6.8 + (avg_speed_kmh - 15.0) * 0.4
    elif avg_speed_kmh < 25.0:
        base_met = 8.8 + (avg_speed_kmh - 20.0) * 0.44
    elif avg_speed_kmh < 30.0:
        base_met = 11.0 + (avg_speed_kmh - 25.0) * 0.3
    else:
        base_met = 12.5 + min(3.0, (avg_speed_kmh - 30.0) * 0.2)

    # Ogni livello di resistenza (da 1 a 8) aggiunge circa il 14% di carico di potenza
    clamped_res = max(1, min(8, resistance_level))
    resistance_factor = 1.0 + (clamped_res - 1) * 0.14

    # Correzione BMI (il costo metabolico aumenta leggermente per masse corporee maggiori)
    bmi_factor = 1.0 + max(-0.1, min(0.25, (bmi - 22.0) * 0.012))

    effective_met = base_met * resistance_factor * bmi_factor

    # Formula ACSM: Kcal = MET * 3.5 * weight(kg) / 200 * duration(minutes)
    calories = (effective_met * 3.5 * weight / 200.0) * (duration_seconds / 60.0)
    return round(max(1.0, calories), 1)

def calculate_journey_calories(distance_km: float, profile: Optional[UserProfile]) -> int:
    """Calcola le calorie stimate necessarie per percorrere una determinata distanza sulla cyclette"""
    weight = profile.current_weight_kg if profile and profile.current_weight_kg else 70.0
    # Consumo medio su cyclette a ritmo costante: ~0.38 kcal/kg per km
    kcal_per_km = weight * 0.38
    return int(round(distance_km * kcal_per_km))
