from tests.conftest import TestingSessionLocal, client
from app.schemas import BodyCompositionCreate


def test_schema_normalizer_italian_and_strings():
    raw_data = {
        "peso": "122,40 kg",
        "bmi": "38.2",
        "grasso_corporeo": "37,4 %",
        "grasso_sottocutaneo": "31.7%",
        "grasso_viscerale": "20",
        "massa_muscolare": "72,83 kg",
        "percentuale_muscolo_scheletrica": "40.2 %",
        "massa_ossea": "3.79 kg",
        "peso_senza_grassi": "76.62 kg",
        "età_metabolica": "43",
        "bmr": "2006 kcal",
        "acqua_corporea": "45.2 %",
        "proteine": "14.3 %",
        "data": "2026-11-03"
    }
    model = BodyCompositionCreate.model_validate(raw_data)
    assert model.weight_kg == 122.40
    assert model.bmi == 38.2
    assert model.body_fat_pct == 37.4
    assert model.subcutaneous_fat_pct == 31.7
    assert model.visceral_fat == 20.0
    assert model.muscle_mass_kg == 72.83
    assert model.skeletal_muscle_pct == 40.2
    assert model.bone_mass_kg == 3.79
    assert model.fat_free_mass_kg == 76.62
    assert model.metabolic_age == 43
    assert model.bmr_kcal == 2006.0
    assert model.body_water_pct == 45.2
    assert model.protein_pct == 14.3
    assert str(model.recorded_at) == "2026-11-03"


def test_body_composition_crud_and_deltas():
    # 1. Register test user
    reg = client.post("/api/auth/register", json={
        "username": "bio_user",
        "password": "password123",
        "full_name": "Bio Tester"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add first entry (e.g. baseline 1 week ago)
    entry1_data = {
        "recorded_at": "2026-10-27",
        "weight_kg": 124.0,
        "bmi": 38.7,
        "body_fat_pct": 38.5,
        "subcutaneous_fat_pct": 32.5,
        "visceral_fat": 21.0,
        "muscle_mass_kg": 72.5,
        "skeletal_muscle_pct": 39.8,
        "bone_mass_kg": 3.79,
        "fat_free_mass_kg": 76.29,
        "metabolic_age": 44,
        "bmr_kcal": 2015.0,
        "body_water_pct": 44.5,
        "protein_pct": 14.0,
        "notes": "Prima rilevazione di partenza"
    }
    res1 = client.post("/api/profile/body-composition", json=entry1_data, headers=headers)
    assert res1.status_code == 200
    item1 = res1.json()
    assert item1["weight_kg"] == 124.0
    assert item1["delta"] is None

    # 3. Add second entry via bulk-json (e.g. today)
    bulk_payload = {
        "recorded_at": "2026-11-03",
        "raw_json": """{
            "peso": "122.40 kg",
            "bmi": 38.2,
            "grasso_corporeo": "37.4%",
            "grasso_sottocutaneo": "31.7%",
            "grasso_viscerale": 20,
            "massa_muscolare": "72.83 kg",
            "percentuale_muscolo_scheletrica": "40.2%",
            "massa_ossea": "3.79 kg",
            "peso_senza_grassi": "76.62 kg",
            "età_metabolica": 43,
            "bmr": 2006,
            "acqua_corporea": "45.2%",
            "proteine": "14.3%"
        }"""
    }
    res2 = client.post("/api/profile/body-composition/bulk-json", json=bulk_payload, headers=headers)
    assert res2.status_code == 200
    item2 = res2.json()
    assert item2["weight_kg"] == 122.40
    assert item2["delta"] is not None
    assert item2["delta"]["days"] == 7
    assert item2["delta"]["weight_kg"] == -1.6  # 122.40 - 124.00
    assert item2["delta"]["body_fat_pct"] == -1.1  # 37.4 - 38.5
    assert item2["delta"]["muscle_mass_kg"] == 0.33  # 72.83 - 72.50
    assert item2["delta"]["visceral_fat"] == -1.0  # 20 - 21

    # 4. GET /api/profile/body-composition
    res_list = client.get("/api/profile/body-composition", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 2
    assert items[0]["id"] == item2["id"]
    assert items[0]["delta"]["weight_kg"] == -1.6
    assert items[1]["id"] == item1["id"]
    assert items[1]["delta"] is None

    # 5. Check user profile current_weight_kg was updated to latest
    # 5. Check user profile and set complete profile data
    res_prof = client.put("/api/profile", json={
        "birth_date": "1992-05-15",
        "gender": "male",
        "height_cm": 178.0,
        "target_weight_kg": 85.0,
        "daily_calorie_target": 2100
    }, headers=headers)
    assert res_prof.status_code == 200

    # 6. GET /api/profile/body-composition/ai-review
    res_ai = client.get("/api/profile/body-composition/ai-review", headers=headers)
    assert res_ai.status_code == 200
    ai_data = res_ai.json()
    assert "review_markdown" in ai_data
    assert len(ai_data["review_markdown"]) > 20
    assert "overall_trend" in ai_data
    assert len(ai_data["recommendations"]) > 0

    # 7. DELETE entry
    del_res = client.delete(f"/api/profile/body-composition/{item1['id']}", headers=headers)
    assert del_res.status_code == 204

    # Verify only 1 remains
    res_list_after = client.get("/api/profile/body-composition", headers=headers)
    assert res_list_after.status_code == 200
    assert len(res_list_after.json()) == 1
