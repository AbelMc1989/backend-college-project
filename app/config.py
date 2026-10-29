import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    """Базовая конфигурация приложения."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-flask-secret-key")
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "dev-jwt-secret-key-at-least-32-bytes-long-for-hs256"
    )
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    """Конфигурация для локальной разработки (по умолчанию SQLite, поддержка PostgreSQL через DATABASE_URL)."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'ecommerce.db'}"
    )


class TestingConfig(BaseConfig):
    """Конфигурация для запуска автотестов (изолированная БД в оперативной памяти)."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-key- strictly-for-automated-tests"


class ProductionConfig(BaseConfig):
    """Промышленная конфигурация (требует явного задания переменных окружения)."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
