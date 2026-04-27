import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Crypto Price Predictor"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Feature Flags
    USE_S3: bool = os.getenv("USE_S3", "False").lower() == "true"
    USE_POSTGRES: bool = os.getenv("USE_POSTGRES", "False").lower() == "true"
    USE_REDIS: bool = os.getenv("USE_REDIS", "False").lower() == "true"

    # Database (Postgres / Supabase)
    DB_URL: str = os.getenv("DB_URL", os.getenv("SUPABASE_DB_URL", "postgresql://postgres:password@db.supabase.co:5432/postgres"))
    SQLITE_URL: str = "sqlite:///registry.db"

    # Storage (MinIO / Supabase S3)
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", os.getenv("SUPABASE_S3_ACCESS_KEY", "minio"))
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", os.getenv("SUPABASE_S3_SECRET_KEY", "miniopassword"))
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "models")

    # Local Storage
    # Use path relative to this file so it works regardless of cwd
    LOCAL_STORAGE_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models_storage"
    )

    # Redis (Upstash or Redis Cloud — set USE_REDIS=true + REDIS_URL in env)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PREDICTION_TTL: int = int(os.getenv("REDIS_PREDICTION_TTL", "3600"))   # 1 hour
    REDIS_OHLCV_TTL: int = int(os.getenv("REDIS_OHLCV_TTL", "300"))              # 5 minutes
    REDIS_VALIDATION_TTL: int = int(os.getenv("REDIS_VALIDATION_TTL", "86400"))  # 24 hours

    # Prediction store — how old a cached prediction can be before re-running inference
    PREDICTION_STALE_HOURS: int = int(os.getenv("PREDICTION_STALE_HOURS", "24"))

    # Admin
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    class Config:
        case_sensitive = True

settings = Settings()
