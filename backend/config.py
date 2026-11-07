import os
from pathlib import Path

# Project root directory (authoritative anchor for all relative paths)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Auto-load untracked .env file if present (without external dependencies)
def _load_env_file():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            pass

_load_env_file()

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

# Environment classification ('development', 'staging', 'production')
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

class ConfigurationError(ValueError):
    """Raised when runtime environment configuration violates safety invariants."""


def validate_database_environment(env_name: Optional[str] = None, db_url: Optional[str] = None) -> None:
    """
    Enforces fail-closed database configuration across runtime environments.

    Invariants:
    - In production (or staging when strict):
      * DATABASE_URL is strictly required.
      * DATABASE_URL must start with 'postgresql://' or 'postgres://'.
      * Local SQLite configurations or fallbacks raise ConfigurationError immediately.
      * Unreachable or malformed PostgreSQL URLs fail closed.
    - In development / local testing:
      * Missing DATABASE_URL allows default local SQLite.
      * SQLite URLs and PostgreSQL URLs are both permitted.
    """
    env = (env_name if env_name is not None else os.getenv("ENVIRONMENT", "development")).strip().lower()
    url = (db_url if db_url is not None else os.getenv("DATABASE_URL", "")).strip()

    if env == "production":
        if not url:
            raise ConfigurationError(
                "Production Configuration Error: DATABASE_URL must be configured when ENVIRONMENT=production. "
                "Silent fallback to local SQLite is strictly prohibited."
            )
        if url.startswith("sqlite://") or "://" not in url:
            raise ConfigurationError(
                "Production Configuration Error: SQLite database cannot be used when ENVIRONMENT=production. "
                "Production requires a managed PostgreSQL database."
            )
        if not url.startswith(("postgresql://", "postgres://")):
            raise ConfigurationError(
                "Production Configuration Error: DATABASE_URL must use 'postgresql://' or 'postgres://' scheme in production."
            )


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
