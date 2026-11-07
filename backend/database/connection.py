"""
Centralized Database Access Layer (DAL)
=======================================
Provides a unified, thread-safe, and PEP 249-compliant database interface
supporting both:
1. SQLite (default for local development, reproducible regression testing, and CI).
2. PostgreSQL (for cloud deployment targeting ₹0/month on Neon Serverless PostgreSQL).

Architectural Decision Note:
---------------------------
SQLAlchemy Core and heavyweight ORMs were evaluated and deliberately excluded.
Introducing an ORM would add significant dependency overhead (~40,000 lines of library code),
require rewriting 80+ existing parameterized SQL queries into proprietary expression syntax,
and increase attack surface without performance benefits. Instead, this lightweight
DAL provides direct connection pooling, context management, credentials masking, and
query placeholder translation with zero third-party bloat.

Security & Governance Invariants:
--------------------------------
- Credentials are NEVER logged or displayed in string representations.
- Database URLs are sanitized with `mask_database_url()`.
- Invalid configurations fail loudly via `DatabaseConfigurationError`.
- Connection failures to PostgreSQL NEVER silently fall back to SQLite.
- Point-in-time financial data immutability and publication date checks are preserved.
"""

from __future__ import annotations

import os
import re
import logging
import sqlite3
import threading
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

from backend.config import PROJECT_ROOT, get_database_path, DATABASE_PATH, validate_database_environment, ConfigurationError

logger = logging.getLogger(__name__)

# Pattern to identify SQL tokens where placeholders must NOT be replaced:
# 1. Single-quoted strings (including escaped single quotes '')
# 2. Double-quoted identifiers (including escaped double quotes "")
# 3. Single-line SQL comments (-- ...)
# 4. Multi-line SQL block comments (/* ... */)
_SQL_SKIP_PATTERN = re.compile(
    r"'(''|[^'])*'"
    r'|"(""|[^"])*"'
    r"|--[^\r\n]*"
    r"|/\*[\s\S]*?\*/",
    re.MULTILINE,
)


class DatabaseEngine(str, Enum):
    """Supported database engines."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DatabaseError(Exception):
    """Base exception for all database access layer operations."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration, URL scheme, or driver is invalid."""


class DatabaseConnectionError(DatabaseError):
    """Raised when acquiring or connecting to a database fails."""


class DatabaseQueryError(DatabaseError):
    """Raised when executing a database query fails."""


# Pattern to match credentials in URLs even with special characters
_URL_CREDENTIAL_PATTERN = re.compile(
    r"^(?P<prefix>[a-zA-Z0-9_+.-]+://[^:/@]+:)(?P<password>.*)(?P<suffix>@[^/@]+(?::\d+)?(?:/.*)?)$"
)


def mask_database_url(url: str) -> str:
    """
    Masks credentials in a database connection URL for safe logging and diagnostics.
    
    Examples
    --------
    >>> mask_database_url("postgresql://user:secret@ep-cool-db.neon.tech/main?sslmode=require")
    'postgresql://user:***@ep-cool-db.neon.tech/main?sslmode=require'
    >>> mask_database_url("sqlite:///database/swing_trading.db")
    'sqlite:///database/swing_trading.db'
    """
    if not url:
        return ""
    try:
        # Regex match handles passwords with special characters including '@'
        m = _URL_CREDENTIAL_PATTERN.match(url)
        if m:
            return f"{m.group('prefix')}***{m.group('suffix')}"

        parts = urlsplit(url)
        if not parts.scheme:
            return url
        if parts.password is not None:
            user = parts.username or ""
            host = parts.hostname or ""
            port = f":{parts.port}" if parts.port else ""
            masked_netloc = f"{user}:***@{host}{port}"
            return urlunsplit((parts.scheme, masked_netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:
        return "<malformed_database_url>"


class DatabaseConfig:
    """Immutable parsed database configuration."""

    def __init__(
        self,
        engine: DatabaseEngine,
        raw_url: str,
        masked_url: str,
        db_path: Optional[Path] = None,
    ):
        self.engine = engine
        self.raw_url = raw_url
        self.masked_url = masked_url
        self.db_path = db_path

    @property
    def is_sqlite(self) -> bool:
        return self.engine == DatabaseEngine.SQLITE

    @property
    def is_postgresql(self) -> bool:
        return self.engine == DatabaseEngine.POSTGRESQL

    def __repr__(self) -> str:
        return f"DatabaseConfig(engine={self.engine.value}, url='{self.masked_url}')"


def parse_database_url(url: Optional[Union[str, Path, os.PathLike]] = None) -> DatabaseConfig:
    """
    Parses and validates database connection configuration.
    
    Resolution order:
    1. Explicit `url` or `Path` argument passed to this function.
    2. `DATABASE_URL` environment variable if present.
    3. Default to SQLite anchored at `get_database_path()`.

    Raises
    ------
    DatabaseConfigurationError
        If URL scheme is unsupported or malformed.
    """
    # Check if DATABASE_URL environment variable is set
    env_target = os.getenv("DATABASE_URL", "").strip()

    # Determine if url is the default DATABASE_PATH sentinel or None
    is_default_target = (
        url is None
        or url is DATABASE_PATH
        or (isinstance(url, (str, Path, os.PathLike)) and str(url) == str(DATABASE_PATH))
    )

    # Enforce environment guard for database configuration
    active_env = os.getenv("ENVIRONMENT", "development").strip().lower()
    target_for_validation = env_target if is_default_target else (str(url).strip() if url is not None else "")
    validate_database_environment(env_name=active_env, db_url=target_for_validation)

    if is_default_target and env_target:
        target_url = env_target
    elif is_default_target:
        sqlite_path = get_database_path()
        raw_url = f"sqlite:///{sqlite_path}"
        return DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            raw_url=raw_url,
            masked_url=raw_url,
            db_path=sqlite_path,
        )
    elif isinstance(url, (Path, os.PathLike)):
        str_val = str(url).strip()
        if str_val.startswith(("postgresql://", "postgres://", "sqlite://")):
            target_url = str_val
        else:
            resolved = Path(url).resolve()
            raw = f"sqlite:///{resolved}"
            return DatabaseConfig(
                engine=DatabaseEngine.SQLITE,
                raw_url=raw,
                masked_url=raw,
                db_path=resolved,
            )
    else:
        target_url = str(url).strip()

    # 2. Local file path without scheme (e.g. 'database/staging.db' or ':memory:')
    if "://" not in target_url:
        if target_url == ":memory:":
            return DatabaseConfig(
                engine=DatabaseEngine.SQLITE,
                raw_url="sqlite:///:memory:",
                masked_url="sqlite:///:memory:",
                db_path=None,
            )
        p = Path(target_url)
        resolved_path = (PROJECT_ROOT / p).resolve() if not p.is_absolute() else p.resolve()
        raw_url = f"sqlite:///{resolved_path}"
        return DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            raw_url=raw_url,
            masked_url=raw_url,
            db_path=resolved_path,
        )

    # 3. SQLite URL scheme
    if target_url.startswith("sqlite://"):
        path_part = target_url[len("sqlite://") :]
        if path_part.startswith("/"):
            path_part = path_part[1:]

        if path_part == ":memory:":
            db_path = None
        else:
            p = Path(path_part)
            db_path = (PROJECT_ROOT / p).resolve() if not p.is_absolute() else p.resolve()
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

        return DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            raw_url=target_url,
            masked_url=target_url,
            db_path=db_path,
        )

    # 4. PostgreSQL URL scheme
    if target_url.startswith(("postgresql://", "postgres://")):
        masked = mask_database_url(target_url)
        return DatabaseConfig(
            engine=DatabaseEngine.POSTGRESQL,
            raw_url=target_url,
            masked_url=masked,
            db_path=None,
        )

    # 5. Unsupported or malformed scheme
    masked_target = mask_database_url(target_url)
    raise DatabaseConfigurationError(
        f"Unsupported database scheme in URL: '{masked_target}'. "
        f"Supported schemes are 'sqlite://' or 'postgresql://' / 'postgres://'."
    )


class DbRow:
    """
    Lightweight dictionary- and index-accessible row wrapper for PostgreSQL.
    Provides identical ergonomics to `sqlite3.Row`:
    - Access by column name: `row["symbol"]`
    - Access by index: `row[0]`
    - Dict conversion: `dict(row)`
    - Iteration: `for val in row`
    """
    __slots__ = ("_data", "_mapping")

    def __init__(self, data: Sequence[Any], mapping: Dict[str, int]):
        self._data = tuple(data)
        self._mapping = mapping

    def __getitem__(self, key: Union[int, str]) -> Any:
        if isinstance(key, int):
            return self._data[key]
        idx = self._mapping.get(key)
        if idx is None:
            raise KeyError(f"Column '{key}' not found in row. Available: {list(self._mapping.keys())}")
        return self._data[idx]

    def get(self, key: str, default: Any = None) -> Any:
        idx = self._mapping.get(key)
        return self._data[idx] if idx is not None else default

    def keys(self) -> Sequence[str]:
        return list(self._mapping.keys())

    def values(self) -> Tuple[Any, ...]:
        return self._data

    def items(self) -> Iterator[Tuple[str, Any]]:
        for k, idx in self._mapping.items():
            yield k, self._data[idx]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            return dict(self.items()) == other
        if isinstance(other, (tuple, list)):
            return self._data == tuple(other)
        return False


def _adapt_query_placeholders(query: str, target_engine: DatabaseEngine) -> str:
    """
    Adapts positional and named parameter markers between SQL dialects:
    - SQLite -> PostgreSQL: translates '?' to '%s' and ':param' to '%(param)s'
      (ignoring literals, identifiers, comments, and double colons '::type').
    - PostgreSQL -> SQLite: translates '%s' to '?' (ignoring literals, identifiers, and comments).
    """
    if target_engine == DatabaseEngine.POSTGRESQL and ("?" in query or ":" in query):
        def _replace_segment(text: str) -> str:
            if "?" in text:
                text = text.replace("?", "%s")
            if ":" in text:
                text = re.sub(r'(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)', r'%(\1)s', text)
            return text

        parts: List[str] = []
        last_end = 0
        for match in _SQL_SKIP_PATTERN.finditer(query):
            start, end = match.span()
            parts.append(_replace_segment(query[last_end:start]))
            parts.append(query[start:end])
            last_end = end
        parts.append(_replace_segment(query[last_end:]))
        return "".join(parts)

    if target_engine == DatabaseEngine.SQLITE and "%s" in query:
        parts: List[str] = []
        last_end = 0
        for match in _SQL_SKIP_PATTERN.finditer(query):
            start, end = match.span()
            parts.append(query[last_end:start].replace("%s", "?"))
            parts.append(query[start:end])
            last_end = end
        parts.append(query[last_end:].replace("%s", "?"))
        return "".join(parts)

    return query


class CursorWrapper:
    """Unified cursor wrapper conforming to PEP 249 with dialet-aware adaptation."""

    def __init__(self, raw_cursor: Any, engine: DatabaseEngine):
        self._raw_cursor = raw_cursor
        self._engine = engine
        self._col_mapping: Optional[Dict[str, int]] = None

    @property
    def raw_cursor(self) -> Any:
        return self._raw_cursor

    @property
    def engine(self) -> DatabaseEngine:
        return self._engine

    @property
    def description(self) -> Any:
        return self._raw_cursor.description

    @property
    def rowcount(self) -> int:
        return self._raw_cursor.rowcount

    @property
    def lastrowid(self) -> Optional[int]:
        if self._engine == DatabaseEngine.SQLITE:
            return getattr(self._raw_cursor, "lastrowid", None)
        return None

    def _build_col_mapping(self):
        desc = self._raw_cursor.description
        if desc:
            self._col_mapping = {col[0]: idx for idx, col in enumerate(desc)}
        else:
            self._col_mapping = None

    def execute(self, query: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> CursorWrapper:
        adapted_sql = _adapt_query_placeholders(query, self._engine)
        try:
            if params is not None:
                self._raw_cursor.execute(adapted_sql, params)
            else:
                self._raw_cursor.execute(adapted_sql)
            self._build_col_mapping()
            return self
        except Exception as e:
            logger.error(f"Database query failed [{self._engine.value}]: {e} | Query: {adapted_sql[:200]}")
            raise DatabaseQueryError(f"Query execution failed: {e}") from e

    def executemany(self, query: str, seq_of_params: Sequence[Union[Sequence[Any], Dict[str, Any]]]) -> CursorWrapper:
        adapted_sql = _adapt_query_placeholders(query, self._engine)
        try:
            self._raw_cursor.executemany(adapted_sql, seq_of_params)
            self._build_col_mapping()
            return self
        except Exception as e:
            logger.error(f"Database executemany failed [{self._engine.value}]: {e} | Query: {adapted_sql[:200]}")
            raise DatabaseQueryError(f"Batch query execution failed: {e}") from e

    def fetchone(self) -> Optional[Any]:
        row = self._raw_cursor.fetchone()
        if row is None:
            return None
        if self._engine == DatabaseEngine.SQLITE:
            return row
        if self._col_mapping is not None:
            return DbRow(row, self._col_mapping)
        return row

    def fetchall(self) -> List[Any]:
        rows = self._raw_cursor.fetchall()
        if not rows:
            return []
        if self._engine == DatabaseEngine.SQLITE:
            return list(rows)
        if self._col_mapping is not None:
            return [DbRow(r, self._col_mapping) for r in rows]
        return list(rows)

    def fetchmany(self, size: Optional[int] = None) -> List[Any]:
        rows = self._raw_cursor.fetchmany(size) if size is not None else self._raw_cursor.fetchmany()
        if not rows:
            return []
        if self._engine == DatabaseEngine.SQLITE:
            return list(rows)
        if self._col_mapping is not None:
            return [DbRow(r, self._col_mapping) for r in rows]
        return list(rows)

    def close(self):
        try:
            self._raw_cursor.close()
        except Exception:
            pass

    def __iter__(self) -> Iterator[Any]:
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row

    def __enter__(self) -> CursorWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ConnectionWrapper:
    """Unified connection wrapper providing transaction management and cursor generation."""

    def __init__(self, raw_conn: Any, engine: DatabaseEngine, is_pooled: bool = False):
        self._raw_conn = raw_conn
        self._engine = engine
        self._is_pooled = is_pooled
        self._is_closed = False

    @property
    def raw_connection(self) -> Any:
        return self._raw_conn

    @property
    def engine(self) -> DatabaseEngine:
        return self._engine

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    def cursor(self) -> CursorWrapper:
        if self._is_closed:
            raise DatabaseConnectionError("Cannot open cursor on a closed connection.")
        try:
            raw_cur = self._raw_conn.cursor()
            return CursorWrapper(raw_cur, self._engine)
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to acquire cursor: {e}") from e

    def execute(self, query: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> CursorWrapper:
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        if not self._is_closed:
            self._raw_conn.commit()

    def rollback(self):
        if not self._is_closed:
            try:
                self._raw_conn.rollback()
            except Exception:
                pass

    def close(self):
        if not self._is_closed:
            self._is_closed = True
            try:
                self._raw_conn.close()
            except Exception as e:
                logger.debug(f"Exception during connection close: {e}")

    @contextmanager
    def transaction(self) -> Iterator[ConnectionWrapper]:
        """Context manager managing an explicit transaction block without closing the connection."""
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    def __enter__(self) -> ConnectionWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.rollback()
            else:
                try:
                    self.commit()
                except Exception:
                    self.rollback()
                    raise
        finally:
            self.close()


# =============================================================================
# Global Connection Pool & Lifecycle Management
# =============================================================================

_pg_pools: Dict[str, Any] = {}
_pool_lock = threading.Lock()


def _resolve_hostaddr_if_needed(conninfo: str) -> str:
    """
    If local system DNS refuses resolution (e.g. restricted intranet router),
    queries a public resolver (8.8.8.8) and injects 'hostaddr' to allow
    libpq direct connection while preserving TLS certificate validation against host.
    """
    try:
        import socket
        import struct

        parts = urlsplit(conninfo)
        host = parts.hostname
        if not host or "hostaddr=" in conninfo:
            return conninfo

        # Test local resolution first
        try:
            socket.getaddrinfo(host, 5432, family=socket.AF_INET)
            return conninfo
        except socket.gaierror:
            pass

        # Query 8.8.8.8 via UDP
        def _query_dns(hostname: str, dns_ip: str = "8.8.8.8") -> List[str]:
            packet = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            for part in hostname.split("."):
                packet += bytes([len(part)]) + part.encode("ascii")
            packet += b"\x00\x00\x01\x00\x01"

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            sock.sendto(packet, (dns_ip, 53))
            data, _ = sock.recvfrom(1024)
            ips = []
            idx = 12
            while data[idx] != 0:
                idx += data[idx] + 1
            idx += 5
            while idx < len(data):
                if data[idx] & 0xC0 == 0xC0:
                    idx += 2
                else:
                    while data[idx] != 0:
                        idx += data[idx] + 1
                    idx += 1
                rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", data[idx : idx + 10])
                idx += 10
                if rtype == 1 and rdlen == 4:
                    ips.append(socket.inet_ntoa(data[idx : idx + 4]))
                idx += rdlen
            return ips

        ips = _query_dns(host, "8.8.8.8")
        if ips:
            from urllib.parse import parse_qs, urlencode
            qs = parse_qs(parts.query)
            qs["hostaddr"] = [ips[0]]
            new_query = urlencode(qs, doseq=True)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
    except Exception as e:
        logger.debug(f"DNS fallback resolution bypassed: {e}")

    return conninfo


def _get_pg_pool(raw_url: str) -> Any:
    """Initializes and retrieves the thread-safe PostgreSQL connection pool for a specific endpoint."""
    global _pg_pools
    if raw_url in _pg_pools:
        return _pg_pools[raw_url]

    with _pool_lock:
        if raw_url not in _pg_pools:
            try:
                from psycopg_pool import ConnectionPool
            except ImportError as e:
                raise DatabaseConfigurationError(
                    "PostgreSQL driver 'psycopg' and 'psycopg_pool' are required when "
                    "DATABASE_URL is set to a postgresql:// endpoint. "
                    "Install with: pip install 'psycopg[binary]' psycopg-pool"
                ) from e

            # Resolve hostaddr if local DNS refuses
            conninfo_active = _resolve_hostaddr_if_needed(raw_url)
            masked = mask_database_url(conninfo_active)
            logger.info(f"Initializing PostgreSQL connection pool to: {masked}")
            try:
                # Optimized pool sizing for cloud deployment and serverless autosuspend
                is_neon = "neon.tech" in raw_url
                default_min = "0" if is_neon else "1"
                pool_min = int(os.getenv("DB_POOL_MIN_SIZE", default_min))
                pool_max = int(os.getenv("DB_POOL_MAX_SIZE", "5" if is_neon else "10"))
                max_idle = float(os.getenv("DB_POOL_MAX_IDLE", "120.0" if is_neon else "600.0"))

                pool = ConnectionPool(
                    conninfo=conninfo_active,
                    min_size=pool_min,
                    max_size=pool_max,
                    max_idle=max_idle,
                    timeout=30.0,
                    open=True,
                )
                _pg_pools[raw_url] = pool
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection pool to {masked}: {e}")
                raise DatabaseConnectionError(f"Could not connect to PostgreSQL database: {e}") from e

    return _pg_pools[raw_url]


def close_db_pool():
    """Drains and closes all active PostgreSQL connection pools."""
    global _pg_pools
    with _pool_lock:
        for p in list(_pg_pools.values()):
            try:
                p.close()
            except Exception as e:
                logger.debug(f"Exception closing connection pool: {e}")
        _pg_pools.clear()


def reset_db_pool():
    """Testing utility: closes all pools and resets global connection state."""
    close_db_pool()


def open_db_connection(
    db_target: Optional[Union[str, Path, os.PathLike]] = None,
    timeout: float = 30.0,
) -> ConnectionWrapper:
    """
    Opens and returns a managed ConnectionWrapper.
    Callers can use transaction context managers (`with conn:`) or explicitly call `conn.close()`.
    """
    config = parse_database_url(db_target)

    if config.engine == DatabaseEngine.SQLITE:
        if config.db_path is None:
            # In-memory SQLite
            try:
                raw_conn = sqlite3.connect(":memory:", timeout=timeout)
                raw_conn.row_factory = sqlite3.Row
                raw_conn.execute("PRAGMA foreign_keys = ON;")
            except Exception as e:
                raise DatabaseConnectionError(f"Failed to open in-memory SQLite connection: {e}") from e
        else:
            try:
                raw_conn = sqlite3.connect(str(config.db_path), timeout=timeout)
                raw_conn.row_factory = sqlite3.Row
                raw_conn.execute("PRAGMA foreign_keys = ON;")
            except Exception as e:
                raise DatabaseConnectionError(f"Failed to open SQLite database at '{config.db_path}': {e}") from e

        return ConnectionWrapper(raw_conn, DatabaseEngine.SQLITE, is_pooled=False)

    elif config.engine == DatabaseEngine.POSTGRESQL:
        pool = _get_pg_pool(config.raw_url)
        try:
            raw_conn = pool.getconn(timeout=timeout)
        except Exception as e:
            masked = config.masked_url
            logger.error(f"PostgreSQL connection acquisition failed for {masked}: {e}")
            raise DatabaseConnectionError(f"Failed to acquire PostgreSQL connection: {e}") from e

        class _PooledPgConnection:
            """Adapter returning connection to the pool upon close()."""
            def __init__(self, conn, p):
                self._conn = conn
                self._p = p
                self._closed = False

            def cursor(self):
                return self._conn.cursor()

            def execute(self, *args, **kwargs):
                return self._conn.execute(*args, **kwargs)

            def commit(self):
                self._conn.commit()

            def rollback(self):
                self._conn.rollback()

            def close(self):
                if not self._closed:
                    self._closed = True
                    try:
                        # Ensure any uncommitted transaction is rolled back before returning to pool
                        self._conn.rollback()
                    except Exception:
                        pass
                    try:
                        self._p.putconn(self._conn)
                    except Exception:
                        pass

        pooled_adapter = _PooledPgConnection(raw_conn, pool)
        return ConnectionWrapper(pooled_adapter, DatabaseEngine.POSTGRESQL, is_pooled=True)

    raise DatabaseConfigurationError(f"Unsupported database engine: {config.engine}")


@contextmanager
def get_db_connection(
    db_target: Optional[Union[str, Path, os.PathLike]] = None,
    timeout: float = 30.0,
) -> Iterator[ConnectionWrapper]:
    """
    Context manager yielding a managed database connection.
    Handles acquisition and automatically guarantees connection cleanup on exit.
    """
    conn = open_db_connection(db_target, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_cursor(
    db_target: Optional[Union[str, Path, os.PathLike]] = None,
    commit: bool = True,
    timeout: float = 30.0,
) -> Iterator[CursorWrapper]:
    """
    Convenience context manager yielding an active database cursor directly.
    Commits on successful block completion (if `commit=True`), rolls back on exception,
    and automatically cleans up cursor and connection handles.
    """
    with get_db_connection(db_target, timeout=timeout) as conn:
        with conn.cursor() as cur:
            try:
                yield cur
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
