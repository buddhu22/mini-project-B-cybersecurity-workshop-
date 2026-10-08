"""Environment-backed configuration for the workshop directory."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "local-development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'workshop.db').as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_SECRET_KEY = os.getenv("FLASK_JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15")) * 60
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("REFRESH_TOKEN_DAYS", "1")) * 24 * 60 * 60
    JWT_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    JWT_COOKIE_CSRF_PROTECT = False  # Flask-WTF protects cookie-authenticated form/AJAX POSTs.
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_COOKIE_NAME = "workshop_access_token"
    JWT_REFRESH_COOKIE_NAME = "workshop_refresh_token"
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_REFRESH_COOKIE_PATH = "/"
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
