# ===================================
# BALIKESİR SON DAKİKA HABER
# app/config/settings.py
# ===================================

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os
from pathlib import Path

# Proje kök dizini
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Uygulama ayarları — .env dosyasından okunur.
    Tüm ayarlar environment variable olarak da geçersiz kılınabilir.
    """

    # --- Uygulama ---
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Balıkesir Son Dakika Haber"
    APP_VERSION: str = "1.0.0"

    # --- Güvenlik ---
    SECRET_KEY: str = "change-me-to-a-strong-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # --- Veritabanı ---
    DATABASE_URL: str = f"sqlite+aiosqlite:///./data/database.sqlite3"

    # --- Site Bilgileri ---
    SITE_NAME: str = "Balıkesir Son Dakika Haber"
    SITE_URL: str = "http://127.0.0.1:8000"
    SITE_DESCRIPTION: str = "Balıkesir ve ilçelerinden son dakika haberleri"

    # --- Admin ---
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@balikesirsondakikahaber.com"
    INTERNAL_API_KEY: str = "my-super-secret-internal-key-for-pc-worker"

    # --- AI Servisi ---
    AI_PROVIDER: str = "none"
    AI_API_KEY: Optional[str] = None
    
    # --- NVIDIA NEMOTRON ---
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b"
    NVIDIA_API_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_TEMPERATURE: float = 1.0
    NVIDIA_TOP_P: float = 0.95
    NVIDIA_MAX_TOKENS: int = 16384
    NVIDIA_REASONING_EFFORT: str = "medium"
    NVIDIA_REASONING_BUDGET: int = 16384
    NVIDIA_STREAM: bool = True
    NVIDIA_TIMEOUT: int = 180
    
    # Timeout Ayarları (Eski)
    NVIDIA_TIMEOUT_CONNECT: int = 10
    NVIDIA_TIMEOUT_READ: int = 180
    NVIDIA_TIMEOUT_WRITE: int = 30
    NVIDIA_TIMEOUT_POOL: int = 30

    # --- Media Fallback & API ---
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None

    # --- RSS & Haber Toplama ---
    RSS_FETCH_INTERVAL_MINUTES: int = 15
    MAX_ARTICLES_PER_SOURCE: int = 50

    # --- Dosya Yükleme ---
    UPLOAD_DIR: str = "./data/media"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- CORS ---
    ALLOWED_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def database_is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @property
    def upload_dir_path(self) -> Path:
        return BASE_DIR / self.UPLOAD_DIR.lstrip("./")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Singleton instance — uygulamanın her yerinden import edilir
settings = Settings()
