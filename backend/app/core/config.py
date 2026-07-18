from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

# Load only this backend's optional local file. Existing shell/ECS environment
# values win, so injected production secrets are never overridden by a file.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    sensor_interval_seconds: float = float(os.getenv("SENSOR_INTERVAL_SECONDS", "1"))
    anomaly_cooldown_seconds: int = int(os.getenv("ANOMALY_COOLDOWN_SECONDS", "30"))
    anomaly_frequency: float = float(os.getenv("ANOMALY_FREQUENCY", "0.02"))
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_model: str = os.getenv("LLM_MODEL", "openrouter/free")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
    event_database_provider: str = os.getenv("EVENT_DATABASE_PROVIDER", "sqlite").lower()
    sqlite_database_url: str | None = os.getenv("SQLITE_DATABASE_URL") or None
    aws_region: str | None = os.getenv("AWS_REGION") or None
    dynamodb_table_name: str | None = os.getenv("DYNAMODB_TABLE_NAME") or None
    bedrock_model_id: str | None = os.getenv("BEDROCK_MODEL_ID") or None
    cors_allowed_origins_raw: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]


settings = Settings()
