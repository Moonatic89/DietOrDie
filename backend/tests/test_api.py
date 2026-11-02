import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Setup test DB in memory con StaticPool per condividere l'in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_register_and_login():
    res = client.post("/api/auth/register", json={
        "username": "user1",
        "password": "secretpassword123",
        "full_name": "Mario Rossi"
    })
    assert res.status_code == 200
    token1 = res.json()["access_token"]
    assert token1 is not None

    res2 = client.post("/api/auth/register", json={
        "username": "user2",
        "password": "secretpassword456",
        "full_name": "Anna Rossi"
    })
    assert res2.status_code == 200
    token2 = res2.json()["access_token"]
    assert token2 is not None

    res_users = client.get("/api/auth/users-list")
    assert res_users.status_code == 200
    usernames = [u["username"] for u in res_users.json()]
    assert "user1" in usernames
    assert "user2" in usernames

def test_profile_and_metrics():
    login_res = client.post("/api/auth/login-json", json={
        "username": "user1",
        "password": "secretpassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    prof_res = client.put("/api/profile", json={
        "height_cm": 180.0,
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "gender": "male",
        "activity_level": "moderate"
    }, headers=headers)
    assert prof_res.status_code == 200

    metrics_res = client.get("/api/profile/metrics", headers=headers)
    assert metrics_res.status_code == 200
    data = metrics_res.json()
    assert data["bmi"] == 24.7
    assert data["bmi_category"] == "Normopeso"
    assert data["recommended_calories"] > 0

def test_log_ride_and_journey_progress():
    login_res = client.post("/api/auth/login-json", json={
        "username": "user1",
        "password": "secretpassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ride_res = client.post("/api/rides", json={
        "duration_seconds": 1800,
        "distance_km": 20.0
    }, headers=headers)
    assert ride_res.status_code == 200
    ride_data = ride_res.json()
    assert ride_data["ride"]["distance_km"] == 20.0
    assert ride_data["ride"]["avg_speed_kmh"] == 40.0
    assert ride_data["progress"] is not None
    assert ride_data["progress"]["cumulative_distance_km"] == 20.0

def test_esp32_endpoint():
    res = client.post("/api/rides/esp32", json={
        "api_key": "esp32-dietordie-secret-token",
        "username": "user1",
        "duration_seconds": 900,
        "distance_km": 5.0,
        "avg_speed_kmh": 20.0,
        "calories_burned": 120.0
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ride"]["distance_km"] == 5.0
    assert data["progress"]["cumulative_distance_km"] == 25.0

def test_esp32_streaming_5s_aggregation():
    # Simulazione invio telemetria ogni 5 secondi con session_uid
    session_uid = "esp32-test-workout-1"

    # Tick 1 a 5 secondi: 0.03 km percorsi
    t1 = client.post("/api/rides/esp32", json={
        "api_key": "esp32-dietordie-secret-token",
        "username": "user1",
        "session_uid": session_uid,
        "duration_seconds": 5,
        "distance_km": 0.03,
        "current_speed_kmh": 21.6,
        "rpm": 68.0,
        "resistance_level": 4
    })
    assert t1.status_code == 200
    ride_id = t1.json()["ride"]["id"]
    assert t1.json()["progress"]["cumulative_distance_km"] == 25.03

    # Tick 2 a 10 secondi: 0.06 km percorsi
    t2 = client.post("/api/rides/esp32", json={
        "api_key": "esp32-dietordie-secret-token",
        "username": "user1",
        "session_uid": session_uid,
        "duration_seconds": 10,
        "distance_km": 0.06,
        "current_speed_kmh": 21.6,
        "rpm": 68.0,
        "resistance_level": 4
    })
    assert t2.status_code == 200
    assert t2.json()["ride"]["id"] == ride_id  # Stessa sessione aggiornata!
    assert t2.json()["ride"]["duration_seconds"] == 10
    assert t2.json()["ride"]["distance_km"] == 0.06
    assert t2.json()["progress"]["cumulative_distance_km"] == 25.06

def test_mqtt_telemetry_processing():
    import asyncio
    from app.services.mqtt_service import mqtt_service

    mqtt_service.set_session_factory(TestingSessionLocal)

    payload = {
        "user": "user1",
        "session_uid": "mqtt-test-session-1",
        "pulses": 200,
        "distance_km": 1.06,
        "speed_kmh": 24.5,
        "rpm": 76.0,
        "duration_sec": 120,
        "resistance": 3
    }
    # Esegue process_telemetry
    asyncio.run(mqtt_service.process_telemetry(payload))

    # Verifica che la corsa sia stata salvata e leggibile via API
    login_res = client.post("/api/auth/login", data={"username": "user1", "password": "secretpassword123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    res = client.get("/api/rides/active", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    active = res.json()
    assert active is not None
    assert active["distance_km"] == 1.06
    assert active["rpm"] == 76.0
    assert active["resistance_level"] == 3


def test_websocket_endpoint():
    with client.websocket_connect("/api/ws/rides") as ws:
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"


