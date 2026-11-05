import pytest
from tests.conftest import client
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


def test_merge_rides_and_performance_endpoint():
    # Login as user1
    login_res = client.post("/api/auth/login-json", json={
        "username": "user1",
        "password": "secretpassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Log ride 1
    r1_res = client.post("/api/rides", json={
        "duration_seconds": 300,
        "distance_km": 2.0,
        "resistance_level": 2,
        "notes": "Sessione 1 prima del calo tensione"
    }, headers=headers)
    assert r1_res.status_code == 200
    r1_id = r1_res.json()["ride"]["id"]

    # Log ride 2
    r2_res = client.post("/api/rides", json={
        "duration_seconds": 600,
        "distance_km": 4.0,
        "resistance_level": 2,
        "notes": "Sessione 2 dopo riavvio ESP"
    }, headers=headers)
    assert r2_res.status_code == 200
    r2_id = r2_res.json()["ride"]["id"]

    # Test merge endpoint
    merge_payload = {"ride_ids": [r1_id, r2_id]}
    resp = client.post("/api/rides/merge", json=merge_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["id"] == r1_id
    assert data["duration_seconds"] == 900
    assert data["distance_km"] == 6.0
    assert data["total_pedal_strokes"] > 0
    assert data["calories_burned"] > 0
    assert "Unite sessioni" in data["notes"]

    # Test performance endpoint for merged ride
    perf_resp = client.get(f"/api/rides/{r1_id}/performance", headers=headers)
    assert perf_resp.status_code == 200, perf_resp.text
    perf_data = perf_resp.json()

    assert perf_data["ride_id"] == r1_id
    assert perf_data["duration_seconds"] == 900
    assert perf_data["distance_km"] == 6.0
    assert len(perf_data["telemetry_points"]) > 0
    assert len(perf_data["splits"]) >= 1
    assert "zones" in perf_data
    assert perf_data["avg_watts"] > 0

    # Test delete endpoint
    del_resp = client.delete(f"/api/rides/{r1_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Confirm deleted
    get_perf_deleted = client.get(f"/api/rides/{r1_id}/performance", headers=headers)
    assert get_perf_deleted.status_code == 404
