import os
from datetime import timedelta


class Config:
    # [SECURITY] Must be set via environment variable in production.
    # These fallback values are for development only and MUST NOT be used in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION-USE-STRONG-RANDOM-SECRET")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION-USE-STRONG-RANDOM-JWT-SECRET")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,        # Allow up to 20 persistent connections
        "max_overflow": 40,     # Allow 40 additional overflow connections
        "pool_recycle": 300,    # Recycle connections after 5 minutes
        "pool_pre_ping": True,  # Test connection health before use
        "pool_timeout": 10,     # Only wait 10s for a connection (fail fast)
    }
    # [SECURITY - VULN-05 FIX] Set JWT tokens to expire after 8 hours.
    # Previously set to False (never expires), which is a security risk.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ADMIN_IMPORT_TOKEN = os.environ.get("ADMIN_IMPORT_TOKEN", "admin123")

