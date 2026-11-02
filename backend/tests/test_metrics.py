from datetime import date
from app.services.metrics import calculate_bmi, calculate_bmr, calculate_tdee

def test_calculate_bmi():
    # Peso 75kg, altezza 175cm -> BMI 24.5 (Normopeso)
    bmi, category = calculate_bmi(75.0, 175.0)
    assert bmi == 24.5
    assert category == "Normopeso"

    # Peso 95kg, altezza 175cm -> BMI 31.0 (Obesità di classe I)
    bmi, category = calculate_bmi(95.0, 175.0)
    assert bmi == 31.0
    assert "Obesità" in category

def test_calculate_bmr():
    # Uomo 35 anni, 80kg, 180cm
    # 10*80 + 6.25*180 - 5*35 + 5 = 800 + 1125 - 175 + 5 = 1755
    bmr_m = calculate_bmr(80.0, 180.0, 35, "male")
    assert bmr_m == 1755.0

    # Donna 30 anni, 60kg, 165cm
    # 10*60 + 6.25*165 - 5*30 - 161 = 600 + 1031.25 - 150 - 161 = 1320.2
    bmr_f = calculate_bmr(60.0, 165.0, 30, "female")
    assert bmr_f == 1320.2

def test_calculate_tdee():
    bmr = 1500.0
    # Sedentario: 1500 * 1.2 = 1800
    assert calculate_tdee(bmr, "sedentary") == 1800.0
    # Moderato: 1500 * 1.55 = 2325
    assert calculate_tdee(bmr, "moderate") == 2325.0
