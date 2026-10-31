"""
Cache Service for Engine Computations
=====================================

Provides high-performance, thread-safe, memory-bounded caching for:
1. Universe ranking and decision results
2. Sector evaluations
3. Single stock opportunity scores

Invalidation Rules:
-------------------
- Strict point-in-time correctness: cache keys strictly incorporate evaluation_date.
  Historical evaluations NEVER share cache entries with different evaluation dates or live data.
- Data Fingerprint: Computes an ultra-fast (<1ms) fingerprint from SQLite
  (MAX(date) and COUNT(*) of daily_prices, MAX(id) and COUNT(*) of quarterly_results).
  If market data or financial data changes, the fingerprint changes immediately,
  invalidating stale entries.
- Time-To-Live (TTL): 120 seconds maximum lifetime per cache entry.
- Max size per cache to bound memory usage.
"""

import time
import threading
from typing import Any, Dict, Optional, Tuple


_lock = threading.Lock()

# In-memory stores
_universe_ranking_cache: Dict[Tuple[str, Optional[str]], Tuple[float, Any]] = {}
_universe_scores_cache: Dict[Tuple[str, Optional[str]], Tuple[float, Dict[str, Any]]] = {}
_sector_cache: Dict[Tuple[str, str, Optional[str], Tuple[int, ...]], Tuple[float, Any]] = {}
_symbol_score_cache: Dict[Tuple[str, str, Optional[str]], Tuple[float, Any]] = {}

CACHE_TTL_SECONDS = 120.0
MAX_CACHE_ENTRIES = 100


def get_db_fingerprint() -> str:
    """
    Returns an ultra-fast fingerprint of the underlying SQLite tables.
    Runs in < 1ms.
    """
    try:
        import sqlite3
        from backend.data_pipeline.data_service import DATABASE_PATH
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT MAX(date), COUNT(*) FROM daily_prices")
        dp_row = cur.fetchone() or (None, 0)
        cur.execute("SELECT MAX(id), COUNT(*) FROM quarterly_results")
        qr_row = cur.fetchone() or (None, 0)
        conn.close()
        return f"dp:{dp_row[0]}:{dp_row[1]}_qr:{qr_row[0]}:{qr_row[1]}"
    except Exception:
        return "default"


def clear_all_caches():
    """Clears all in-memory caches. Useful in tests or on data reload."""
    with _lock:
        _universe_ranking_cache.clear()
        _universe_scores_cache.clear()
        _sector_cache.clear()
        _symbol_score_cache.clear()


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
    return None


def set_cached_universe_ranking(
    evaluation_date: Optional[str],
    ranking_payload: Any,
    scores_map: Optional[Dict[str, Any]] = None,
):
    fp = get_db_fingerprint()
    key = (fp, evaluation_date)
    now = time.time()
    with _lock:
        if len(_universe_ranking_cache) >= MAX_CACHE_ENTRIES:
            _universe_ranking_cache.clear()
        _universe_ranking_cache[key] = (now, ranking_payload)

        if scores_map is not None:
            if len(_universe_scores_cache) >= MAX_CACHE_ENTRIES:
                _universe_scores_cache.clear()
            _universe_scores_cache[key] = (now, scores_map)


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
    return None


# =============================================================================
# Sector Performance Evaluation Cache
# =============================================================================

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
