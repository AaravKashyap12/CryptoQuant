import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Crypto Price Predictor"
    DEBUG: bool = True
    
    # Feature Flags
    USE_S3: bool = os.getenv("USE_S3", "False").lower() == "true"
    USE_POSTGRES: bool = os.getenv("USE_POSTGRES", "False").lower() == "true"
    
    # Database (Postgres)
    # Default to sqlite if not using postgres
    DB_URL: str = os.getenv("DB_URL", os.getenv("SUPABASE_DB_URL", "postgresql://postgres:password@db.supabase.co:5432/postgres"))
    SQLITE_URL: str = "sqlite:///registry.db"
    
    # Storage (MinIO/S3)
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", os.getenv("SUPABASE_S3_ACCESS_KEY", "minio"))
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", os.getenv("SUPABASE_S3_SECRET_KEY", "miniopassword"))
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "models")
    
    # Local Storage
    LOCAL_STORAGE_DIR: str = os.path.join(os.getcwd(), "data", "models_storage")
    
    class Config:
        case_sensitive = True

settings = Settings()
