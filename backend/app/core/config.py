from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "HealTheCrop API"
    ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./healthecrop.db"

    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Seeded once at startup if no user with this email exists yet (see
    # app/core/admin_seed.py). No default credentials ship in source — set
    # both via environment variables / .env to enable seeding a new admin
    # account. Leaving either unset simply skips seeding (logged), it does
    # not touch any admin account already present in the database.
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173", "http://localhost:4173",
        "http://127.0.0.1:5173", "http://127.0.0.1:4173",
    ]

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_IMAGES: str = "healthecrop-images"
    MINIO_BUCKET_REPORTS: str = "healthecrop-reports"
    LOCAL_STORAGE_FALLBACK_DIR: str = "./storage/local"

    CROP_MODEL_PATH: str = "../ml/models/crop_model.joblib"
    CROP_METADATA_PATH: str = "../ml/data/crop_metadata.json"
    FERTILITY_RULES_PATH: str = "../ml/data/fertility_recommendations.json"
    DISEASE_MODEL_PATH: str = "../cv/models/plant_disease_model.h5"
    DISEASE_CLASS_INDEX_PATH: str = "../cv/models/class_indices.json"
    DISEASE_KB_PATH: str = "../cv/data/disease_knowledge_base.json"

    WEATHER_API_KEY: str = ""
    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"


@lru_cache
def get_settings() -> Settings:
    return Settings()
