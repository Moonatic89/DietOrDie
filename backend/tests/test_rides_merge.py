import pytest
from app.models import User, RideSession
from app.auth import get_password_hash, create_access_token
from app.services.metrics import calculate_mechanical_watts, append_telemetry_tick, generate_ride_performance


def test_mechanical_watts_calculation():
    # Speed 20 km/h, resistance 1
    w1 = calculate_mechanical_watts(20.0, 1)
    assert w1 > 0
    # Higher resistance should yield higher watts
    w4 = calculate_mechanical_watts(20.0, 4)
    assert w4 > w1


def test_append_telemetry_tick():
    hist = append_telemetry_tick(None, 0, 15.0, 60.0, 0.0, 1)
    assert hist is not None
    hist2 = append_telemetry_tick(hist, 5, 18.0, 65.0, 0.025, 1)
    import json
    data = json.loads(hist2)
    assert len(data) == 2
    assert data[1]["sec"] == 5
    assert data[1]["speed"] == 18.0


def test_merge_rides_and_performance_endpoint(client, db_session):
    # Setup test user and auth token
    user = User(
        username="cyclist1",
        email="cyclist1@example.com",
        password_hash=get_password_hash("password123"),
        weight_kg=75.0,
        height_cm=175.0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}

    # Create two fragmented rides
    r1 = RideSession(
        user_id=user.id,
        duration_seconds=300,  # 5 min
        distance_km=2.0,
        avg_speed_kmh=24.0,
        rpm=70.0,
        total_pedal_strokes=571,
        resistance_level=2,
        calories_burned=40.0,
        notes="Sessione 1 prima del calo tensione"
    )
    r2 = RideSession(
        user_id=user.id,
        duration_seconds=600,  # 10 min
        distance_km=4.0,
        avg_speed_kmh=24.0,
        rpm=72.0,
        total_pedal_strokes=1143,
        resistance_level=2,
        calories_burned=85.0,
        notes="Sessione 2 dopo riavvio ESP"
    )
    db_session.add(r1)
    db_session.add(r2)
    db_session.commit()
    db_session.refresh(r1)
    db_session.refresh(r2)

    # Test merge endpoint
    merge_payload = {"ride_ids": [r1.id, r2.id]}
    resp = client.post("/api/rides/merge", json=merge_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["id"] == r1.id
    assert data["duration_seconds"] == 900
    assert data["distance_km"] == 6.0
    assert data["total_pedal_strokes"] == 571 + 1143
    assert data["calories_burned"] > 0
    assert "Unite sessioni" in data["notes"]

    # Verify second ride was deleted from database
    r2_check = db_session.query(RideSession).filter(RideSession.id == r2.id).first()
    assert r2_check is None

    # Test performance endpoint for merged ride
    perf_resp = client.get(f"/api/rides/{r1.id}/performance", headers=headers)
    assert perf_resp.status_code == 200, perf_resp.text
    perf_data = perf_resp.json()

    assert perf_data["ride_id"] == r1.id
    assert perf_data["duration_seconds"] == 900
    assert perf_data["distance_km"] == 6.0
    assert len(perf_data["telemetry_points"]) > 0
    assert len(perf_data["splits"]) >= 1
    assert "zones" in perf_data
    assert perf_data["avg_watts"] > 0

    # Test delete endpoint
    del_resp = client.delete(f"/api/rides/{r1.id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Confirm deletion
    r1_check = db_session.query(RideSession).filter(RideSession.id == r1.id).first()
    assert r1_check is None
