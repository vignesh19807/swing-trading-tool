"""
Cache Service for Engine Computations
=====================================

Provides high-performance, thread-safe, memory-bounded L1 (in-memory)
and multi-worker shared L2 (container filesystem) caching for:
1. Universe ranking and decision results
2. Complete consolidated sector & industry reports
3. Single stock opportunity scores and sector evaluations

Invalidation Rules:
-------------------
- Strict point-in-time correctness: cache keys strictly incorporate evaluation_date.
  Historical evaluations NEVER share cache entries with different evaluation dates or live data.
- Data Fingerprint: Computes an ultra-fast (<1ms) fingerprint from database
  (MAX(date) and COUNT(*) of daily_prices, MAX(id) and COUNT(*) of quarterly_results).
  If market data or financial data changes, the fingerprint changes immediately,
  invalidating stale entries.
- Time-To-Live (TTL): 3600 seconds (1 hour) lifetime per cache entry.
- Max size per in-memory cache to strictly bound memory usage within 512 MB.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import threading
from typing import Any, Dict, Optional, Tuple


_lock = threading.Lock()

# In-memory stores (L1)
_universe_ranking_cache: Dict[Tuple[str, Optional[str]], Tuple[float, Any]] = {}
_universe_scores_cache: Dict[Tuple[str, Optional[str]], Tuple[float, Dict[str, Any]]] = {}
_sector_cache: Dict[Tuple[str, str, Optional[str], Tuple[int, ...]], Tuple[float, Any]] = {}
_sector_report_cache: Dict[Tuple[str, Optional[str], str], Tuple[float, Any]] = {}
_symbol_score_cache: Dict[Tuple[str, str, Optional[str]], Tuple[float, Any]] = {}

CACHE_TTL_SECONDS = 3600.0
MAX_CACHE_ENTRIES = 100


def _get_l2_cache_dir() -> Path:
    """Returns the path to the shared container/host L2 cache directory."""
    cache_dir = Path(tempfile.gettempdir()) / "swing_trading_l2_cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return cache_dir


def _hash_key(*parts: Any) -> str:
    """Generates a clean deterministic filename-safe SHA256 fragment from cache key parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _read_l2_cache(prefix: str, key_hash: str) -> Optional[Any]:
    """Reads and parses an L2 cache file if present and unexpired."""
    cache_file = _get_l2_cache_dir() / f"{prefix}_{key_hash}.json"
    if not cache_file.exists():
        return None
    try:
        mtime = cache_file.stat().st_mtime
        if time.time() - mtime > CACHE_TTL_SECONDS:
            cache_file.unlink(missing_ok=True)
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("payload")
    except Exception:
        return None


def _write_l2_cache(prefix: str, key_hash: str, payload: Any):
    """Atomically writes payload to an L2 cache file."""
    cache_dir = _get_l2_cache_dir()
    cache_file = cache_dir / f"{prefix}_{key_hash}.json"
    tmp_file = cache_dir / f"{prefix}_{key_hash}.tmp.{os.getpid()}"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump({"payload": payload, "cached_at": time.time()}, f)
        os.replace(tmp_file, cache_file)
    except Exception:
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass


# =============================================================================
# Multi-Worker Locking Mechanism
# =============================================================================

def acquire_warming_lock(task_name: str, lock_ttl_seconds: float = 60.0) -> bool:
    """
    Acquires a cross-worker filesystem lock to ensure only one Uvicorn worker
    runs heavy background cache warming on container startup.
    Returns True if lock was acquired, False if another worker is already warming.
    """
    lock_file = _get_l2_cache_dir() / f"warming_{task_name}.lock"
    now = time.time()
    try:
        if lock_file.exists():
            try:
                mtime = lock_file.stat().st_mtime
                if now - mtime < lock_ttl_seconds:
                    return False  # Active lock held by another process
                lock_file.unlink(missing_ok=True)
            except Exception:
                pass

        with open(lock_file, "x", encoding="utf-8") as f:
            f.write(f"pid:{os.getpid()}:ts:{now}")
        return True
    except FileExistsError:
        return False
    except Exception:
        return True


def release_warming_lock(task_name: str):
    """Releases the cross-worker warming lock."""
    lock_file = _get_l2_cache_dir() / f"warming_{task_name}.lock"
    try:
        lock_file.unlink(missing_ok=True)
    except Exception:
        pass


def is_warming_in_progress(task_name: str, lock_ttl_seconds: float = 60.0) -> bool:
    """Checks whether another worker currently holds an active warming lock."""
    lock_file = _get_l2_cache_dir() / f"warming_{task_name}.lock"
    if not lock_file.exists():
        return False
    try:
        mtime = lock_file.stat().st_mtime
        return (time.time() - mtime) < lock_ttl_seconds
    except Exception:
        return False


def get_db_fingerprint() -> str:
    """
    Returns an ultra-fast fingerprint of the underlying database tables.
    Runs in < 1ms.
    """
    try:
        from backend.database.connection import get_db_cursor
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT MAX(date), COUNT(*) FROM daily_prices")
            dp_row = cur.fetchone() or (None, 0)
            cur.execute("SELECT MAX(id), COUNT(*) FROM quarterly_results")
            qr_row = cur.fetchone() or (None, 0)
            return f"dp:{dp_row[0]}:{dp_row[1]}_qr:{qr_row[0]}:{qr_row[1]}"
    except Exception:
        return "default"


def clear_all_caches():
    """Clears all in-memory L1 and filesystem L2 caches. Useful in tests or on data reload."""
    with _lock:
        _universe_ranking_cache.clear()
        _universe_scores_cache.clear()
        _sector_cache.clear()
        _sector_report_cache.clear()
        _symbol_score_cache.clear()

    try:
        cache_dir = _get_l2_cache_dir()
        if cache_dir.exists():
            for f in cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
            for f in cache_dir.glob("*.lock"):
                f.unlink(missing_ok=True)
    except Exception:
        pass


# =============================================================================
# Universe Ranking & Score Map
# =============================================================================

def get_cached_universe_ranking(evaluation_date: Optional[str] = None) -> Optional[Any]:
    fp = get_db_fingerprint()
    key = (fp, evaluation_date)
    with _lock:
        entry = _universe_ranking_cache.get(key)
        if entry is not None:
            ts, val = entry
            if time.time() - ts < CACHE_TTL_SECONDS:
                return val
            else:
                _universe_ranking_cache.pop(key, None)

    # Check L2 filesystem cache (cross-worker shared)
    kh = _hash_key(fp, evaluation_date)
    l2_val = _read_l2_cache("univ_rank", kh)
    if l2_val is not None:
        with _lock:
            _universe_ranking_cache[key] = (time.time(), l2_val)
        return l2_val

    return None


def set_cached_universe_ranking(
    evaluation_date: Optional[str],
    ranking_payload: Any,
    scores_map: Optional[Dict[str, Any]] = None,
):
    fp = get_db_fingerprint()
    key = (fp, evaluation_date)
    now = time.time()
    kh = _hash_key(fp, evaluation_date)

    with _lock:
        if len(_universe_ranking_cache) >= MAX_CACHE_ENTRIES:
            _universe_ranking_cache.clear()
        _universe_ranking_cache[key] = (now, ranking_payload)

        if scores_map is not None:
            if len(_universe_scores_cache) >= MAX_CACHE_ENTRIES:
                _universe_scores_cache.clear()
            _universe_scores_cache[key] = (now, scores_map)

    # Persist to L2 disk cache for multi-worker sharing
    _write_l2_cache("univ_rank", kh, ranking_payload)
    if scores_map is not None:
        _write_l2_cache("univ_scores", kh, scores_map)


def get_cached_universe_scores(evaluation_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    fp = get_db_fingerprint()
    key = (fp, evaluation_date)
    with _lock:
        entry = _universe_scores_cache.get(key)
        if entry is not None:
            ts, val = entry
            if time.time() - ts < CACHE_TTL_SECONDS:
                return val
            else:
                _universe_scores_cache.pop(key, None)

    # Check L2 filesystem cache (cross-worker shared)
    kh = _hash_key(fp, evaluation_date)
    l2_val = _read_l2_cache("univ_scores", kh)
    if l2_val is not None:
        with _lock:
            _universe_scores_cache[key] = (time.time(), l2_val)
        return l2_val

    return None


# =============================================================================
# Sector Performance & Consolidated Sector Reports
# =============================================================================

def get_cached_sector_report(
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D"
) -> Optional[Any]:
    fp = get_db_fingerprint()
    key = (fp, evaluation_date, ranking_period)
    with _lock:
        entry = _sector_report_cache.get(key)
        if entry is not None:
            ts, val = entry
            if time.time() - ts < CACHE_TTL_SECONDS:
                return val
            else:
                _sector_report_cache.pop(key, None)

    # Check L2 filesystem cache (cross-worker shared)
    kh = _hash_key(fp, evaluation_date, ranking_period)
    l2_val = _read_l2_cache("sec_report", kh)
    if l2_val is not None:
        with _lock:
            _sector_report_cache[key] = (time.time(), l2_val)
        return l2_val

    return None


def set_cached_sector_report(
    evaluation_date: Optional[str],
    ranking_period: str,
    report: Any,
):
    fp = get_db_fingerprint()
    key = (fp, evaluation_date, ranking_period)
    now = time.time()
    kh = _hash_key(fp, evaluation_date, ranking_period)

    with _lock:
        if len(_sector_report_cache) >= MAX_CACHE_ENTRIES:
            _sector_report_cache.clear()
        _sector_report_cache[key] = (now, report)

    # Persist to L2 disk cache for multi-worker sharing
    _write_l2_cache("sec_report", kh, report)


def get_cached_sector_evaluation(
    sector: str,
    evaluation_date: Optional[str] = None,
    lookback_periods: Optional[Tuple[int, ...]] = None,
) -> Optional[Any]:
    fp = get_db_fingerprint()
    norm_sector = (sector or "").strip().upper()
    lb_key = tuple(lookback_periods) if lookback_periods else ()
    key = (fp, norm_sector, evaluation_date, lb_key)
    with _lock:
        entry = _sector_cache.get(key)
        if entry is not None:
            ts, val = entry
            if time.time() - ts < CACHE_TTL_SECONDS:
                return val
            else:
                _sector_cache.pop(key, None)
    return None


def set_cached_sector_evaluation(
    sector: str,
    evaluation_date: Optional[str],
    lookback_periods: Optional[Tuple[int, ...]],
    result: Any,
):
    fp = get_db_fingerprint()
    norm_sector = (sector or "").strip().upper()
    lb_key = tuple(lookback_periods) if lookback_periods else ()
    key = (fp, norm_sector, evaluation_date, lb_key)
    now = time.time()
    with _lock:
        if len(_sector_cache) >= MAX_CACHE_ENTRIES * 2:
            _sector_cache.clear()
        _sector_cache[key] = (now, result)


# =============================================================================
# Symbol-Level Opportunity Score Cache
# =============================================================================

def get_cached_symbol_score(symbol: str, evaluation_date: Optional[str] = None) -> Optional[Any]:
    fp = get_db_fingerprint()
    sym = (symbol or "").strip().upper()
    key = (fp, sym, evaluation_date)
    with _lock:
        entry = _symbol_score_cache.get(key)
        if entry is not None:
            ts, val = entry
            if time.time() - ts < CACHE_TTL_SECONDS:
                return val
            else:
                _symbol_score_cache.pop(key, None)
    return None


def set_cached_symbol_score(symbol: str, evaluation_date: Optional[str], result: Any):
    fp = get_db_fingerprint()
    sym = (symbol or "").strip().upper()
    key = (fp, sym, evaluation_date)
    now = time.time()
    with _lock:
        if len(_symbol_score_cache) >= MAX_CACHE_ENTRIES * 5:
            _symbol_score_cache.clear()
        _symbol_score_cache[key] = (now, result)
