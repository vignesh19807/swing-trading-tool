"""
AUDIT-035: End-to-End User Journey Verification
================================================
Simulates complete frontend user workflows against FastAPI backend.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_journey_1_market_overview():
    res = client.get("/api/market/indices")
    assert res.status_code == 200
    data = res.json()
    assert "nifty50" in data
    assert "market_regime" in data
    assert "condition" in data
    print("Journey 1 (Market Overview): PASS")

def test_journey_2_opportunities():
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert "opportunities" in data
    assert len(data["opportunities"]) > 0
    opp = data["opportunities"][0]
    assert "symbol" in opp
    assert "opportunity_score" in opp
    print(f"Journey 2 (Opportunities): PASS (Found {len(data['opportunities'])} ranked setups, top: {opp['symbol']})")

def test_journey_3_stock_screener():
    res = client.get("/api/stocks?limit=10&page=1")
    assert res.status_code == 200
    data = res.json()
    assert "stocks" in data
    assert len(data["stocks"]) == 10
    print("Journey 3 (Stock Screener): PASS")

def test_journey_4_stock_detail():
    res = client.get("/api/stocks/SUNPHARMA")
    assert res.status_code == 200
    detail = res.json()
    assert detail["symbol"] == "SUNPHARMA"
    
    res_hist = client.get("/api/stocks/SUNPHARMA/history?timeframe=6M")
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert "candles" in hist
    assert len(hist["candles"]) > 50
    print(f"Journey 4 (Stock Detail SUNPHARMA): PASS (Found {len(hist['candles'])} candles)")

def test_journey_5_sector_explorer():
    res = client.get("/api/sectors")
    assert res.status_code == 200
    sectors = res.json()
    assert "sectors" in sectors
    print(f"Journey 5 (Sector Explorer): PASS (Found {len(sectors['sectors'])} sectors)")

def test_journey_6_backtest_performance():
    res = client.get("/api/backtests/latest")
    assert res.status_code == 200
    bt = res.json()
    assert "status" in bt
    print(f"Journey 6 (Backtest Performance): PASS (Status: {bt['status']})")

if __name__ == "__main__":
    test_journey_1_market_overview()
    test_journey_2_opportunities()
    test_journey_3_stock_screener()
    test_journey_4_stock_detail()
    test_journey_5_sector_explorer()
    test_journey_6_backtest_performance()
    print("\nALL 6 END-TO-END USER JOURNEYS PASSED SUCCESSFULLY!")
