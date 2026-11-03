import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "DietOrDie"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dietordie-super-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days session
    
    # ESP32 Bike Telemetry
    ESP32_API_KEY: str = os.getenv("ESP32_API_KEY", "esp32-dietordie-secret-token")

    # MQTT Broker
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "dietordie/telemetry")
    MQTT_USERNAME: str | None = os.getenv("MQTT_USERNAME", None)
    MQTT_PASSWORD: str | None = os.getenv("MQTT_PASSWORD", None)
    MQTT_ENABLED: bool = os.getenv("MQTT_ENABLED", "true").lower() in ("true", "1", "yes")

    # Database (Default to local SQLite in WAL mode)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dietordie.db")
    
    # AI Vision Keys (OpenRouter free tier prioritized)
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY", None)
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    OPENROUTER_TEXT_MODEL: str = os.getenv("OPENROUTER_TEXT_MODEL", "nvidia/nemotron-3.5-lightning:free")
    
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY", None)
    
    # Domain
    DOMAIN: str = os.getenv("DOMAIN", "dietordie.duckdns.org")

    # Uploads directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
