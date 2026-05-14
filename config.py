import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    _db_path = (BASE_DIR / "instance" / "app.db").resolve()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + str(_db_path).replace("\\", "/"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "55.7558"))
    WEATHER_LON = float(os.environ.get("WEATHER_LON", "37.6173"))

    NOTES_PER_PAGE = 8

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

    ALICE_WEBHOOK_SECRET = os.environ.get("ALICE_WEBHOOK_SECRET", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name: str | None = None):
    key = name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_MAP.get(key, DevelopmentConfig)
