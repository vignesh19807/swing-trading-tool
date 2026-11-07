import os
from pathlib import Path

# Project root directory (authoritative anchor for all relative paths)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Default database directory
DATABASE_DIR = PROJECT_ROOT / "database"

def get_database_path() -> Path:
    """
    Return the authoritative database path.
    Prioritizes DATABASE_PATH environment variable if set.
    Relative paths are resolved anchored to PROJECT_ROOT.
    Defaults to PROJECT_ROOT / 'database' / 'swing_trading.db'.
    """
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        db_path = (PROJECT_ROOT / p).resolve() if not p.is_absolute() else p.resolve()
    else:
        db_path = (DATABASE_DIR / "swing_trading.db").resolve()

    # Ensure parent directory exists safely
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    return db_path


class _DatabasePath(os.PathLike):
    """
    Dynamic Path proxy that always reflects the active database path.
    Integrates transparently with sqlite3.connect(), os.fspath(), and Path operations.
    """
    def __fspath__(self) -> str:
        return str(get_database_path())

    def __str__(self) -> str:
        return str(get_database_path())

    def __repr__(self) -> str:
        return f"DatabasePath('{get_database_path()}')"

    def __eq__(self, other) -> bool:
        if other is None:
            return False
        try:
            return get_database_path() == Path(other).resolve()
        except Exception:
            return False

    def __hash__(self) -> int:
        return hash(get_database_path())

    def __truediv__(self, other):
        return get_database_path() / other

    def __getattr__(self, name):
        return getattr(get_database_path(), name)


# Standardized DATABASE_PATH configurable via environment variable
DATABASE_PATH = _DatabasePath()

# CORS origins
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Market timing & configuration
HISTORY_YEARS = int(os.getenv("HISTORY_YEARS", "2"))
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "Asia/Kolkata")
