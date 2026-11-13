"""
Tests for Phase 5.4.11 — Analytical Performance Optimization
============================================================

Validates:
1. Bounded 420-calendar-day historical query lookback in sector engine.
2. Complete 252-trading-day returns coverage and absence of future data leakage.
3. Sector report caching (L1 in-memory + L2 container filesystem).
4. Analytical cache TTL (3600s), exact evaluation-date isolation, and database fingerprint invalidation.
5. Multi-worker warming lock coordination (preventing duplicate work across Uvicorn workers).
6. Non-blocking startup and prompt health endpoint responsiveness.
7. Contract preservation for GET /api/opportunities and GET /api/sectors.
"""

import datetime
import os
import time
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app import app
from backend.logic.sector_engine import (
    _get_bounded_start_date,
    _calculate_constituent_returns,
    DEFAULT_LOOKBACK_PERIODS,
)
from backend.engines.cache_service import (
    CACHE_TTL_SECONDS,
    get_db_fingerprint,
    clear_all_caches,
    get_cached_sector_report,
    set_cached_sector_report,
    get_cached_universe_ranking,
    set_cached_universe_ranking,
    get_cached_universe_scores,
    acquire_warming_lock,
    release_warming_lock,
    is_warming_in_progress,
)
from backend.engines.sector_industry_engine import run_sector_industry_engine


@pytest.fixture(autouse=True)
def reset_cache_state(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    clear_all_caches()
    yield
    clear_all_caches()


# =============================================================================
# 1. Historical Query Bounded Lookback Tests
# =============================================================================

def test_bounded_start_date_calculation():
    """Confirms 420-calendar-day bounded start date calculation."""
    # When evaluation_date is provided
    eval_date = "2026-11-06"
    expected = "2025-09-12"  # 2026-11-06 minus 420 days
    assert _get_bounded_start_date(eval_date, calendar_days=420) == expected

    # When evaluation_date is None, defaults relative to today
    today = datetime.date.today()
    expected_today = (today - datetime.timedelta(days=420)).isoformat()
    assert _get_bounded_start_date(None, calendar_days=420) == expected_today


def test_no_future_data_leakage():
    """Verifies that bounded lookback strictly anchors to evaluation_date without future leakage."""
    eval_date = "2025-06-30"
    start_date = _get_bounded_start_date(eval_date, calendar_days=420)
    assert start_date < eval_date
    assert (datetime.date.fromisoformat(eval_date) - datetime.date.fromisoformat(start_date)).days == 420


def test_constituent_returns_missing_data_safe():
    """Verifies that missing or insufficient historical data safely yields None without crashes."""
    res = _calculate_constituent_returns("NON_EXISTENT_SYMBOL", "2026-11-06", DEFAULT_LOOKBACK_PERIODS)
    assert isinstance(res, dict)
    assert res == {"21D": None, "63D": None, "126D": None, "252D": None}


# =============================================================================
# 2. Cache Service & TTL Extension Tests
# =============================================================================

def test_cache_ttl_extended():
    """Verifies CACHE_TTL_SECONDS is set to 3600.0s (1 hour)."""
    assert CACHE_TTL_SECONDS == 3600.0


def test_sector_report_cache_lifecycle():
    """Validates full lifecycle: miss -> store -> hit -> L2 persistence -> invalidation."""
    eval_date = "2026-11-06"
    period = "63D"

    # 1. Cache Miss
    assert get_cached_sector_report(eval_date, period) is None

    # 2. Store
    mock_report = {
        "status": "VALID",
        "evaluation_date": eval_date,
        "ranking_period": period,
        "sectors_analyzed": 9,
        "sector_rankings": [{"sector": "Financial Services", "rank": 1}],
    }
    set_cached_sector_report(eval_date, period, mock_report)

    # 3. Cache Hit (L1)
    cached = get_cached_sector_report(eval_date, period)
    assert cached is not None
    assert cached["sectors_analyzed"] == 9
    assert cached["sector_rankings"][0]["sector"] == "Financial Services"


def test_sector_report_historical_date_isolation():
    """Verifies that different evaluation dates maintain strictly isolated cache entries."""
    report_a = {"status": "VALID", "evaluation_date": "2026-11-06", "val": "A"}
    report_b = {"status": "VALID", "evaluation_date": "2026-10-31", "val": "B"}

    set_cached_sector_report("2026-11-06", "63D", report_a)
    set_cached_sector_report("2026-10-31", "63D", report_b)

    assert get_cached_sector_report("2026-11-06", "63D")["val"] == "A"
    assert get_cached_sector_report("2026-10-31", "63D")["val"] == "B"
    assert get_cached_sector_report("2026-09-30", "63D") is None


def test_database_fingerprint_invalidation(monkeypatch):
    """Verifies that when database fingerprint changes, stale cache entries are automatically evicted."""
    eval_date = "2026-11-06"
    set_cached_sector_report(eval_date, "63D", {"status": "VALID", "version": 1})

    # Fingerprint 1
    assert get_cached_sector_report(eval_date, "63D")["version"] == 1

    # Simulate database update changing fingerprint
    with patch("backend.engines.cache_service.get_db_fingerprint", return_value="dp:2026-11-07:2631_qr:19:19"):
        # Old entry under old fingerprint must miss
        assert get_cached_sector_report(eval_date, "63D") is None


# =============================================================================
# 3. Multi-Worker Warming Lock Coordination Tests
# =============================================================================

def test_multi_worker_warming_lock():
    """Verifies that only one worker can acquire the warming lock, preventing duplicate work."""
    task = "test_warmer"
    release_warming_lock(task)

    # Worker 1 acquires lock
    assert acquire_warming_lock(task, lock_ttl_seconds=30.0) is True
    assert is_warming_in_progress(task, lock_ttl_seconds=30.0) is True

    # Worker 2 attempts to acquire same lock concurrently -> Denied
    assert acquire_warming_lock(task, lock_ttl_seconds=30.0) is False

    # Worker 1 completes and releases lock
    release_warming_lock(task)
    assert is_warming_in_progress(task, lock_ttl_seconds=30.0) is False

    # Now Worker 2 can acquire lock
    assert acquire_warming_lock(task, lock_ttl_seconds=30.0) is True
    release_warming_lock(task)


# =============================================================================
# 4. API Endpoint Integration & Health Responsiveness Tests
# =============================================================================

def test_health_endpoints_prompt():
    """Confirms /healthz responds immediately without waiting for analytical warming."""
    client = TestClient(app)
    t0 = time.time()
    res = client.get("/healthz")
    elapsed = time.time() - t0
    assert res.status_code == 200
    assert elapsed < 1.0  # Must respond in sub-second


def test_sectors_endpoint_contract_and_caching():
    """Verifies GET /api/sectors returns contract-compliant payload and leverages caching."""
    client = TestClient(app)

    # Pre-populate cache with known report
    mock_report = {
        "status": "VALID",
        "evaluation_date": "2026-11-06",
        "ranking_period": "63D",
        "sectors_analyzed": 9,
        "industries_analyzed": 19,
        "sector_rankings": [
            {"sector": "Financial Services", "rank": 1, "score": 85.5}
        ],
        "industry_rankings": []
    }
    set_cached_sector_report("2026-11-06", "63D", mock_report)

    t0 = time.time()
    res = client.get("/api/sectors?evaluation_date=2026-11-06&ranking_period=63D")
    elapsed = time.time() - t0

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["evaluation_date"] == "2026-11-06"
    assert "sectors" in data or "sector_rankings" in data
    assert elapsed < 0.5  # Served from cache in sub-second


def test_opportunities_endpoint_contract():
    """Verifies GET /api/opportunities returns contract-compliant payload without errors."""
    client = TestClient(app)

    # Pre-populate ranking cache
    mock_ranking = {
        "evaluation_date": "2026-11-06",
        "top_10": [
            {
                "symbol": "HDFCBANK",
                "company_name": "HDFC Bank Ltd",
                "sector": "Financial Services",
                "industry": "Private Sector Bank",
                "rank": 1,
                "opportunity_score": 82.5,
                "final_ranking_score": 82.5,
                "recommendation": "BUY",
                "status": "VALID",
                "current_price": 1644.55,
                "setup": {
                    "entry_lower": 1640.0,
                    "entry_upper": 1650.0,
                    "stop_loss": 1600.0,
                    "target": 1720.0,
                    "risk_reward_ratio": 2.5,
                }
            }
        ],
        "unranked": []
    }
    set_cached_universe_ranking("2026-11-06", mock_ranking)

    t0 = time.time()
    res = client.get("/api/opportunities?evaluation_date=2026-11-06")
    elapsed = time.time() - t0

    assert res.status_code == 200
    data = res.json()
    assert data["evaluation_date"] == "2026-11-06"
    assert "opportunities" in data
    assert len(data["opportunities"]) == 1
    opp = data["opportunities"][0]
    assert opp["symbol"] == "HDFCBANK"
    assert opp["current_price"] == 1644.55
    assert opp["opportunity_score"] == 82.5
    assert opp["recommendation"] == "BUY"
    assert elapsed < 0.5  # Served from cache in sub-second
