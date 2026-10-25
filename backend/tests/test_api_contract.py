"""
API Contract Verification Test Suite
====================================

Tests all 8 contract endpoints defined in docs/frontend-api-contract.md:
1. GET /healthz/live & /healthz/ready
2. GET /api/market/indices
3. GET /api/opportunities
4. GET /api/stocks
5. GET /api/stocks/{symbol}
6. GET /api/stocks/{symbol}/history
7. GET /api/sectors
8. GET /api/backtests/latest
9. GET /api/data-health
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_healthz_live():
    res = client.get("/healthz/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_healthz_ready():
    res = client.get("/healthz/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["companies_count"] >= 50


def test_market_indices():
    res = client.get("/api/market/indices")
    assert res.status_code == 200
    data = res.json()
    assert "market_regime" in data
    assert "condition" in data
    assert "advancing" in data["condition"]
    assert "declining" in data["condition"]
    assert "nifty50" in data
    assert data["nifty50"]["status"] == "UNAVAILABLE"
    assert "sensex" in data
    assert data["sensex"]["status"] == "UNAVAILABLE"


def test_opportunities():
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert "opportunities" in data
    assert "total_count" in data
    assert isinstance(data["opportunities"], list)
    if data["opportunities"]:
        opp = data["opportunities"][0]
        assert "symbol" in opp
        assert "rank" in opp
        assert "opportunity_score" in opp
        assert "recommendation" in opp


def test_stocks_universe():
    res = client.get("/api/stocks?page=1&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "stocks" in data
    assert "total_count" in data
    assert len(data["stocks"]) <= 10
    if data["stocks"]:
        stk = data["stocks"][0]
        assert "symbol" in stk
        assert "company_name" in stk


def test_stock_detail():
    res = client.get("/api/stocks/INFY")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "INFY"
    assert "identity" in data
    assert "evaluation_date" in data


def test_stock_history():
    res = client.get("/api/stocks/INFY/history")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "INFY"
    assert "candles" in data
    assert len(data["candles"]) > 0
    candle = data["candles"][0]
    assert "date" in candle
    assert "close" in candle


def test_sectors():
    res = client.get("/api/sectors")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "ranking_period" in data


def test_backtest_latest():
    res = client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "total_trades" in data
    assert "win_rate" in data


def test_data_health():
    res = client.get("/api/data-health")
    assert res.status_code == 200
    data = res.json()
    assert "price_data_status" in data
    assert "indicator_status" in data
    assert "pipeline_status" in data
    assert "universe_size" in data
    assert data["universe_size"] >= 50
