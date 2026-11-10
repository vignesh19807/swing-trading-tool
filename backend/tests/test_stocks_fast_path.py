"""
Unit tests for GET /api/stocks Fast-Path Optimization and Historical Cache Integrity
Verifies:
1. Fast-path execution without cached universe scores (null scores).
2. Exact-date cached scores are returned.
3. Undated cached scores (evaluation_date=None) are NOT used as fallback.
4. Scores from another evaluation date are NOT attached.
5. Explicit null representation for missing opportunity scores and recommendations.
6. Pagination behavior (page & limit).
7. Search filtering by symbol and company name.
8. Sector filtering.
9. Technical indicator payload integrity.
10. API contract structure compatibility.
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.app import app, _get_latest_market_date
from backend.engines.cache_service import clear_all_caches, set_cached_universe_ranking

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_caches(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    clear_all_caches()
    yield
    clear_all_caches()


def test_stocks_fast_path_without_cache():
    """Verify endpoint returns quickly with null scores when cache is cold."""
    clear_all_caches()

    t0 = time.time()
    res = client.get("/api/stocks?page=1&limit=50")
    dur = time.time() - t0

    assert res.status_code == 200
    assert dur < 3.0, f"Expected fast-path under 3.0s, took {dur:.2f}s"

    data = res.json()
    assert "page" in data
    assert "limit" in data
    assert "total_count" in data
    assert "stocks" in data
    assert isinstance(data["stocks"], list)
    assert len(data["stocks"]) > 0

    # Verify first stock structure and explicit null score representation
    first = data["stocks"][0]
    assert "symbol" in first
    assert "company_name" in first
    assert "current_price" in first
    assert "technicals" in first
    assert first["opportunity_score"] is None
    assert first["recommendation"] is None

    # Verify technicals object is fully populated
    tech = first["technicals"]
    assert "rsi" in tech
    assert "macd" in tech
    assert "ema20" in tech
    assert "ema50" in tech
    assert "ema200" in tech
    assert "technical_score" in tech


def test_stocks_fast_path_with_exact_date_cached_scores():
    """Verify endpoint uses cached opportunity scores when matching exact evaluation date."""
    clear_all_caches()
    eval_date = _get_latest_market_date()

    mock_score_map = {
        "INFY": {
            "opportunity_score": 85.5,
            "recommendation": "BUY",
            "status": "VALID",
            "rank": 1,
            "final_ranking_score": 88.0,
        }
    }
    # Prime cache strictly with the exact latest evaluation date
    set_cached_universe_ranking(
        evaluation_date=eval_date,
        ranking_payload={"top_10": []},
        scores_map=mock_score_map
    )

    res = client.get("/api/stocks?search=INFY")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    infy = next((s for s in data["stocks"] if s["symbol"] == "INFY"), None)
    assert infy is not None
    assert infy["opportunity_score"] == 85.5
    assert infy["recommendation"] == "BUY"


def test_stocks_rejects_undated_cache_fallback():
    """Verify endpoint does NOT use cached scores stored under evaluation_date=None (no fallback)."""
    clear_all_caches()

    mock_score_map = {
        "INFY": {
            "opportunity_score": 99.9,
            "recommendation": "BUY",
            "status": "VALID",
            "rank": 1,
            "final_ranking_score": 99.9,
        }
    }
    # Store strictly under evaluation_date=None
    set_cached_universe_ranking(
        evaluation_date=None,
        ranking_payload={"top_10": []},
        scores_map=mock_score_map
    )

    res = client.get("/api/stocks?search=INFY")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    infy = next((s for s in data["stocks"] if s["symbol"] == "INFY"), None)
    assert infy is not None
    # Must remain None because exact market date was not primed
    assert infy["opportunity_score"] is None
    assert infy["recommendation"] is None


def test_stocks_rejects_mismatched_historical_date_cache():
    """Verify endpoint does NOT attach scores cached under a different historical date."""
    clear_all_caches()
    different_date = "2020-01-01"

    mock_score_map = {
        "INFY": {
            "opportunity_score": 42.0,
            "recommendation": "SELL",
            "status": "VALID",
            "rank": 10,
            "final_ranking_score": 42.0,
        }
    }
    set_cached_universe_ranking(
        evaluation_date=different_date,
        ranking_payload={"top_10": []},
        scores_map=mock_score_map
    )

    res = client.get("/api/stocks?search=INFY")
    assert res.status_code == 200
    data = res.json()
    infy = next((s for s in data["stocks"] if s["symbol"] == "INFY"), None)
    assert infy is not None
    # Must NOT attach 2020 scores to latest market date
    assert infy["opportunity_score"] is None
    assert infy["recommendation"] is None


def test_stocks_pagination():
    """Verify pagination returns correct slice and preserves total_count."""
    res_p1 = client.get("/api/stocks?page=1&limit=5")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["page"] == 1
    assert data_p1["limit"] == 5
    assert len(data_p1["stocks"]) <= 5
    total = data_p1["total_count"]

    res_p2 = client.get("/api/stocks?page=2&limit=5")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["page"] == 2
    assert data_p2["limit"] == 5
    assert data_p2["total_count"] == total


def test_stocks_search_filtering():
    """Verify search filter by symbol and company name."""
    res = client.get("/api/stocks?search=TCS")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    for s in data["stocks"]:
        assert "tcs" in s["symbol"].lower() or "tcs" in (s["company_name"] or "").lower()


def test_stocks_sector_filtering():
    """Verify sector filter."""
    res_all = client.get("/api/stocks?limit=100")
    assert res_all.status_code == 200
    data_all = res_all.json()
    sectors = {s["sector"] for s in data_all["stocks"] if s.get("sector")}

    if sectors:
        target_sector = list(sectors)[0]
        res_sec = client.get(f"/api/stocks?sector={target_sector}")
        assert res_sec.status_code == 200
        data_sec = res_sec.json()
        assert data_sec["total_count"] >= 1
        for s in data_sec["stocks"]:
            assert s["sector"] == target_sector
