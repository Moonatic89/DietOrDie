import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional
import paho.mqtt.client as mqtt

from app.config import settings
from app.database import SessionLocal
from app.models import User, RideSession, UserJourneyProgress
from app.services.gamification import record_ride_progress, format_progress_response
from app.services.metrics import calculate_ride_calories
from app.routers.websocket import ws_manager

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self, session_factory=None):
        self.client: Optional[mqtt.Client] = None
        self.loop_task: Optional[asyncio.Task] = None
        self.is_running = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._session_factory = session_factory

    def set_session_factory(self, factory):
        self._session_factory = factory

    def _get_db(self):
        if self._session_factory:
            return self._session_factory()
        return SessionLocal()

    def start(self, event_loop: asyncio.AbstractEventLoop):
        if not settings.MQTT_ENABLED:
            logger.info("MQTT disabilitato da configurazione")
            return

        self._main_loop = event_loop
        self.is_running = True

        try:
            # Paho MQTT Client v2
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="dietordie_backend")
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            logger.info(f"Connessione a MQTT Broker {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
            # Usa connect_async per non bloccare lo startup se il broker e temporaneamente offline
            self.client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"Inizializzazione MQTT fallita (il broker potrebbe non essere attivo in locale): {e}")

    def stop(self):
        self.is_running = False
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                logger.warning(f"Errore arresto MQTT: {e}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"MQTT Connesso con successo! Sottoscrizione al topic: {settings.MQTT_TOPIC}")
            client.subscribe(settings.MQTT_TOPIC)
        else:
            logger.warning(f"Connessione MQTT fallita con codice {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"MQTT Disconnesso (rc={rc}). Riconnessione automatica gestita da Paho...")

    def _on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)
            if self._main_loop and self._main_loop.is_running():
                asyncio.run_coroutine_threadsafe(self.process_telemetry(data), self._main_loop)
            else:
                asyncio.run(self.process_telemetry(data))
        except Exception as e:
            logger.error(f"Errore decodifica payload MQTT su {msg.topic}: {e}")

    async def process_telemetry(self, data: dict, db=None):
        """Elabora il payload telemetry ricevuto via MQTT dall'ESP32"""
        username = data.get("username") or data.get("user")
        session_uid = data.get("session_uid")
        distance_km = float(data.get("distance_km", 0.0))
        duration_seconds = int(data.get("duration_seconds", data.get("duration_sec", 0)))
        current_speed_kmh = float(data.get("current_speed_kmh", data.get("speed_kmh", 0.0)))
        avg_speed_kmh = float(data.get("avg_speed_kmh", 0.0))
        rpm = float(data.get("rpm", 0.0))
        resistance_level = int(data.get("resistance_level", data.get("resistance", 1)))
        is_finished = bool(data.get("is_finished", False))

        if distance_km <= 0 and duration_seconds <= 0:
            return

        should_close_db = False
        if db is None:
            db = self._get_db()
            should_close_db = True

        try:
            user = None
            if username:
                user = db.query(User).filter(User.username == username).first()
            if not user:
                user = db.query(User).first()
            if not user:
                return


            hours = duration_seconds / 3600.0 if duration_seconds > 0 else 0.0
            if not avg_speed_kmh or avg_speed_kmh <= 0:
                avg_speed_kmh = round(distance_km / hours, 1) if hours > 0 else current_speed_kmh

            # Calcolo calorie personalizzato per l'utente (peso, altezza, età, BMI, resistenza)
            cal_burned = calculate_ride_calories(
                duration_seconds=duration_seconds,
                distance_km=distance_km,
                avg_speed_kmh=avg_speed_kmh,
                profile=user.profile,
                resistance_level=resistance_level
            )

            # 1. Ricerca sessione attiva (stesso session_uid o aggiornata negli ultimi 60s)
            active_ride = None
            cutoff_time = datetime.utcnow() - timedelta(seconds=60)

            if session_uid:
                active_ride = db.query(RideSession).filter(
                    RideSession.user_id == user.id,
                    RideSession.session_uid == session_uid
                ).first()

            if not active_ride:
                latest_ride = db.query(RideSession).filter(
                    RideSession.user_id == user.id,
                    RideSession.session_uid.isnot(None),
                    RideSession.updated_at >= cutoff_time
                ).order_by(RideSession.updated_at.desc()).first()

                if latest_ride:
                    active_ride = latest_ride

            celebration = None
            progress_resp = None

            if active_ride and not is_finished:
                delta_dist = max(0.0, round(distance_km - active_ride.distance_km, 3))

                active_ride.duration_seconds = duration_seconds
                active_ride.distance_km = distance_km
                active_ride.avg_speed_kmh = avg_speed_kmh
                active_ride.current_speed_kmh = current_speed_kmh
                active_ride.rpm = rpm
                active_ride.resistance_level = resistance_level
                active_ride.calories_burned = cal_burned
                active_ride.updated_at = datetime.utcnow()
                if session_uid and not active_ride.session_uid:
                    active_ride.session_uid = session_uid

                db.commit()
                db.refresh(active_ride)

                if delta_dist > 0:
                    progress_resp, celebration = record_ride_progress(
                        db=db,
                        user_id=user.id,
                        distance_km=delta_dist
                    )
                else:
                    prog = db.query(UserJourneyProgress).filter(
                        UserJourneyProgress.user_id == user.id,
                        UserJourneyProgress.is_active == True
                    ).first()
                    if prog:
                        progress_resp = format_progress_response(prog, db)

                saved_ride = active_ride
            else:
                generated_uid = session_uid or f"esp32_{user.id}_{int(datetime.utcnow().timestamp())}"
                ride = RideSession(
                    user_id=user.id,
                    session_uid=generated_uid,
                    duration_seconds=duration_seconds,
                    distance_km=distance_km,
                    avg_speed_kmh=avg_speed_kmh,
                    current_speed_kmh=current_speed_kmh,
                    rpm=rpm,
                    calories_burned=cal_burned,
                    resistance_level=resistance_level,
                    notes="Ricevuto via MQTT da ESP32",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(ride)
                db.commit()
                db.refresh(ride)

                progress_resp, celebration = record_ride_progress(
                    db=db,
                    user_id=user.id,
                    distance_km=distance_km
                )
                saved_ride = ride

            # Broadcast WebSocket in tempo reale a tutti gli smartphone connessi
            ws_payload = {
                "type": "ride_tick",
                "ride": {
                    "id": saved_ride.id,
                    "user_id": saved_ride.user_id,
                    "username": user.username,
                    "duration_seconds": saved_ride.duration_seconds,
                    "distance_km": saved_ride.distance_km,
                    "avg_speed_kmh": saved_ride.avg_speed_kmh,
                    "current_speed_kmh": saved_ride.current_speed_kmh,
                    "rpm": saved_ride.rpm,
                    "calories_burned": saved_ride.calories_burned,
                    "resistance_level": saved_ride.resistance_level
                },
                "progress": progress_resp.model_dump() if progress_resp else None,
                "celebration": celebration.model_dump() if celebration else None
            }
            await ws_manager.broadcast(ws_payload)

        except Exception as e:
            logger.error(f"Errore elaborazione telemetria MQTT: {e}", exc_info=True)
            db.rollback()
        finally:
            if should_close_db:
                db.close()

mqtt_service = MQTTService()

