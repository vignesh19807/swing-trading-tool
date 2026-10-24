import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Database directory and file
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_DIR.mkdir(exist_ok=True)

# Standardized DATABASE_PATH configurable via environment variable
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(DATABASE_DIR / "swing_trading.db"))
)

# CORS origins
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]

# Market timing & configuration
HISTORY_YEARS = int(os.getenv("HISTORY_YEARS", "2"))
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "Asia/Kolkata")