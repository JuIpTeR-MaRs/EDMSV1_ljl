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
        "pool_size": 25,        # Allow up to 25 persistent connections
        "max_overflow": 50,     # Allow 50 additional overflow connections
        "pool_recycle": 120,    # Recycle connections after 2 minutes to prevent MySQL timeout drops
        "pool_pre_ping": True,  # Test connection health before use (auto-reconnect dead sockets)
        "pool_timeout": 15,     # 15s timeout for obtaining connection
        "connect_args": {
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,
            "charset": "utf8mb4",
            "autocommit": False,
        }
    }
    # [SECURITY - VULN-05 FIX] Set JWT tokens to expire after 8 hours.
    # Previously set to False (never expires), which is a security risk.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ADMIN_IMPORT_TOKEN = os.environ.get("ADMIN_IMPORT_TOKEN", "admin123")

