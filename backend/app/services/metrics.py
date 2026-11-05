from datetime import date
from typing import Optional, Tuple, Any
from app.models import UserProfile, RideSession
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


def calculate_mechanical_watts(speed_kmh: float, resistance_level: int = 1) -> float:
    """Calcola la potenza meccanica istantanea erogata sui pedali (Watts)"""
    clamped_speed = max(0.0, min(50.0, speed_kmh))
    base_watts = 10.0 + 3.8 * clamped_speed
    clamped_res = max(1, min(8, resistance_level))
    res_factor = 0.75 + (clamped_res - 1) * 0.0914
    return round(base_watts * res_factor, 1)


def append_telemetry_tick(
    existing_json: Optional[str],
    sec: int,
    speed: float,
    rpm: float,
    km: float,
    resistance: int = 1
) -> str:
    """Accumula in modo compatto i punti di telemetria nel corso della sessione attiva (max 250 punti)"""
    import json
    try:
        ticks = json.loads(existing_json) if existing_json else []
    except Exception:
        ticks = []

    # Campiona solo se sono trascorsi almeno 4 secondi dall'ultimo punto
    if not ticks or (sec - ticks[-1]["sec"] >= 4):
        watts = calculate_mechanical_watts(speed, resistance)
        ticks.append({
            "sec": int(sec),
            "speed": round(float(speed), 1),
            "rpm": round(float(rpm), 1),
            "km": round(float(km), 3),
            "watts": watts
        })
        # Se supera 250 campioni, dimezza mantenendo i punti rappresentativi
        if len(ticks) > 250:
            ticks = ticks[::2]

    return json.dumps(ticks)


def generate_ride_performance(ride: RideSession):
    """Calcola le metriche analitiche e la serie temporale per il grafico prestazionale"""
    import json
    import math
    from app.schemas import (
        RidePerformanceResponse,
        TelemetryPoint,
        RideSplit,
        IntensityZones
    )

    duration = max(1, ride.duration_seconds)
    distance = max(0.01, ride.distance_km)
    avg_speed = ride.avg_speed_kmh or round((distance / (duration / 3600.0)), 1)
    resistance = ride.resistance_level or 1
    total_pedals = ride.total_pedal_strokes or int(round((distance * 1000.0) / 3.50))
    avg_rpm = ride.rpm or round((total_pedals / (duration / 60.0)), 1)

    points: list[TelemetryPoint] = []
    has_real_ticks = False

    if ride.telemetry_history_json:
        try:
            raw_ticks = json.loads(ride.telemetry_history_json)
            if isinstance(raw_ticks, list) and len(raw_ticks) >= 3:
                has_real_ticks = True
                for t in raw_ticks:
                    points.append(TelemetryPoint(
                        sec=int(t.get("sec", 0)),
                        speed=float(t.get("speed", avg_speed)),
                        rpm=float(t.get("rpm", avg_rpm)),
                        km=float(t.get("km", 0.0)),
                        watts=float(t.get("watts", calculate_mechanical_watts(t.get("speed", avg_speed), resistance)))
                    ))
        except Exception:
            has_real_ticks = False

    # Se non ci sono punti registrati, genera un profilo analitico realistico (pacing fisiologico)
    if not has_real_ticks:
        num_points = min(60, max(15, duration // 30))
        step_sec = max(1, duration // num_points)
        for i in range(num_points + 1):
            t_sec = min(duration, i * step_sec)
            progress_ratio = t_sec / float(duration) if duration > 0 else 1.0

            # Modello fisiologico: riscaldamento primi 10%, passo costante con variazioni, eventuale allungo finale
            if progress_ratio < 0.10:
                pacing = 0.70 + (progress_ratio / 0.10) * 0.30
            elif progress_ratio > 0.90:
                pacing = 1.0 + ((progress_ratio - 0.90) / 0.10) * 0.15
            else:
                # Piccola ondulazione naturale sinusoidale
                wave = math.sin(progress_ratio * math.pi * 6) * 0.06
                pacing = 1.0 + wave

            p_speed = round(max(3.0, avg_speed * pacing), 1)
            p_rpm = round(max(15.0, avg_rpm * pacing), 1)
            p_km = round(distance * progress_ratio, 3)
            p_watts = calculate_mechanical_watts(p_speed, resistance)

            points.append(TelemetryPoint(
                sec=t_sec,
                speed=p_speed,
                rpm=p_rpm,
                km=p_km,
                watts=p_watts
            ))

    speeds = [p.speed for p in points]
    rpms = [p.rpm for p in points]
    watts_list = [p.watts for p in points]

    max_speed = max(speeds) if speeds else avg_speed
    max_rpm = max(rpms) if rpms else avg_rpm
    max_watts = max(watts_list) if watts_list else calculate_mechanical_watts(max_speed, resistance)
    avg_watts = round(sum(watts_list) / len(watts_list), 1) if watts_list else calculate_mechanical_watts(avg_speed, resistance)

    # Calcolo tempo nelle 3 zone di intensità
    z1_sec, z2_sec, z3_sec = 0, 0, 0
    for i in range(len(points)):
        p = points[i]
        dt = (points[i+1].sec - p.sec) if (i + 1 < len(points)) else max(1, duration - p.sec)
        if p.speed < 15.0:
            z1_sec += dt
        elif p.speed <= 22.0:
            z2_sec += dt
        else:
            z3_sec += dt

    tot_z = max(1, z1_sec + z2_sec + z3_sec)
    zones = IntensityZones(
        zone1_recovery_sec=z1_sec,
        zone2_aerobic_sec=z2_sec,
        zone3_threshold_sec=z3_sec,
        zone1_pct=round((z1_sec / tot_z) * 100.0, 1),
        zone2_pct=round((z2_sec / tot_z) * 100.0, 1),
        zone3_pct=round((z3_sec / tot_z) * 100.0, 1)
    )

    # Calcolo split per km
    splits: list[RideSplit] = []
    total_full_kms = int(math.floor(distance))
    prev_split_sec = 0
    prev_split_km = 0.0

    for target_km in range(1, total_full_kms + 1):
        # Trova il punto in cui si supera target_km
        cross_point = next((p for p in points if p.km >= target_km), None)
        if cross_point:
            split_dur = max(1, cross_point.sec - prev_split_sec)
            split_dist = target_km - prev_split_km
            split_speed = round(split_dist / (split_dur / 3600.0), 1) if split_dur > 0 else avg_speed
            split_rpm = cross_point.rpm
            split_w = cross_point.watts
            splits.append(RideSplit(
                km=target_km,
                duration_seconds=split_dur,
                avg_speed_kmh=split_speed,
                avg_rpm=split_rpm,
                avg_watts=split_w
            ))
            prev_split_sec = cross_point.sec
            prev_split_km = target_km

    # Split frazionario finale se residuo >= 0.2 km
    remainder_dist = round(distance - prev_split_km, 2)
    if remainder_dist >= 0.2:
        rem_dur = max(1, duration - prev_split_sec)
        rem_speed = round(remainder_dist / (rem_dur / 3600.0), 1) if rem_dur > 0 else avg_speed
        splits.append(RideSplit(
            km=total_full_kms + 1,
            duration_seconds=rem_dur,
            avg_speed_kmh=rem_speed,
            avg_rpm=avg_rpm,
            avg_watts=avg_watts
        ))

    return RidePerformanceResponse(
        ride_id=ride.id,
        duration_seconds=duration,
        distance_km=round(distance, 2),
        avg_speed_kmh=round(avg_speed, 1),
        max_speed_kmh=round(max_speed, 1),
        avg_rpm=round(avg_rpm, 1),
        max_rpm=round(max_rpm, 1),
        total_pedal_strokes=total_pedals,
        calories_burned=round(ride.calories_burned, 1),
        avg_watts=avg_watts,
        max_watts=max_watts,
        resistance_level=resistance,
        zones=zones,
        splits=splits,
        telemetry_points=points
    )

