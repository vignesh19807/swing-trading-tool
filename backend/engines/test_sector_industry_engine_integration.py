"""
Integration Tests for Sector/Industry Engine
============================================
Validates the complete Sector/Industry intelligence pipeline, ensuring
that the top-level Engine orchestrator successfully queries Data Engineer
classification services, evaluates constituents, ranks groups deterministically,
and exposes relative strength & preliminary scores correctly in a unified report.
"""
import pytest
import pandas as pd
from unittest.mock import patch

from backend.engines.sector_industry_engine import run_sector_industry_engine

# --- Re-use logic layer mocks for end-to-end testing ---
def mock_get_sectors():
    return ["IT", "Banking", "Energy", "Empty Sector"]

def mock_get_industries():
    # Returns a DataFrame per the classification_service contract
    return pd.DataFrame({
        "industry": ["IT Services", "Private Banks", "Refineries", "Empty Industry"],
        "sector": ["IT", "Banking", "Energy", "Empty Sector"]
    })

def mock_get_sector_stocks(sector):
    if sector == "IT": return ["INFY", "TCS"]
    if sector == "Banking": return ["HDFCBANK"]
    if sector == "Energy": return ["RELIANCE"]
    return []

def mock_get_industry_stocks(industry):
    if industry == "IT Services": return ["INFY", "TCS"]
    if industry == "Private Banks": return ["HDFCBANK"]
    if industry == "Refineries": return ["RELIANCE"]
    return []

def mock_get_company_classification(symbol):
    return {"symbol": symbol}

def create_mock_historical_data(symbol, start_price, end_price, length):
    import numpy as np
    if length <= 0:
        return {"status": "EMPTY", "data": pd.DataFrame()}
    prices = np.linspace(start_price, end_price, length)
    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=length, freq="B"),
        "adjusted_close": prices
    })
    return {"symbol": symbol, "status": "VALID", "data": df}

def mock_get_historical_data(symbol, start_date=None, end_date=None, include_adjusted_close=True):
    # Simulate INFY with a +20% return over 300 days (100 -> 120)
    if symbol == "INFY": return create_mock_historical_data(symbol, 100, 120, 300)
    # Simulate TCS with a +10% return over 300 days (100 -> 110)
    elif symbol == "TCS": return create_mock_historical_data(symbol, 100, 110, 300)
    # Simulate HDFCBANK with a +30% return over 300 days (100 -> 130)
    elif symbol == "HDFCBANK": return create_mock_historical_data(symbol, 100, 130, 300)
    # Simulate RELIANCE with a -10% return over 300 days (100 -> 90)
    elif symbol == "RELIANCE": return create_mock_historical_data(symbol, 100, 90, 300)
    # Simulate an incomplete data case
    elif symbol == "INCOMPLETE": return create_mock_historical_data(symbol, 100, 105, 50)
    return {"status": "EMPTY", "data": pd.DataFrame()}

def mock_get_benchmark_historical_data(symbol, start_date=None, end_date=None, include_adjusted_close=True):
    # Simulate Benchmark with exactly +10% return
    if symbol == "NIFTY_50":
        return create_mock_historical_data(symbol, 100, 110, 300)
    return {"status": "EMPTY", "data": pd.DataFrame()}

@pytest.fixture(autouse=True)
def apply_orchestrator_mocks(monkeypatch):
    # Data pipeline level 1 mocks (classification)
    monkeypatch.setattr("backend.engines.sector_industry_engine.get_sectors", mock_get_sectors)
    monkeypatch.setattr("backend.engines.sector_industry_engine.get_industries", mock_get_industries)

    # Data pipeline level 2 mocks (historical logic)
    monkeypatch.setattr("backend.logic.sector_engine.get_sector_stocks", mock_get_sector_stocks)
    monkeypatch.setattr("backend.logic.sector_engine.get_industry_stocks", mock_get_industry_stocks)
    monkeypatch.setattr("backend.logic.sector_engine.get_company_classification", mock_get_company_classification)
    monkeypatch.setattr("backend.logic.sector_engine.get_historical_data", mock_get_historical_data)
    monkeypatch.setattr("backend.logic.sector_engine.get_benchmark_historical_data", mock_get_benchmark_historical_data, raising=False)


# -----------------------------------------------------------------
# INTEGRATION TESTS
# -----------------------------------------------------------------

def test_engine_end_to_end_orchestration():
    """Test standard engine orchestration across all components."""
    report = run_sector_industry_engine(evaluation_date="2025-10-10", ranking_period="63D")

    assert report["status"] == "VALID"
    assert report["evaluation_date"] == "2025-10-10"
    assert report["ranking_period"] == "63D"

    assert report["sectors_analyzed"] == 4
    assert report["industries_analyzed"] == 4

    # Check Sector Rankings structure
    sectors = report["sector_rankings"]
    assert len(sectors) == 4

    # Banking has +30% returns, IT has +15% average, Energy has -10%
    # Rank 1: Banking
    assert sectors[0]["rank"] == 1
    assert sectors[0]["sector"] == "Banking"
    assert sectors[0]["performance"] > 0
    assert sectors[0]["data_quality"] == "VALID"

    # Check that exposed relative strength and score are present in orchestrator output
    assert "relative_strength" in sectors[0]
    assert sectors[0]["relative_strength"]["status"] == "VALID"

    assert "preliminary_score" in sectors[0]
    assert sectors[0]["preliminary_score"]["score"] is not None

    # Rank 2: IT
    assert sectors[1]["rank"] == 2
    assert sectors[1]["sector"] == "IT"

    # Rank 3: Energy
    assert sectors[2]["rank"] == 3
    assert sectors[2]["sector"] == "Energy"

    # Rank None: Empty Sector (Insufficient Data pushes it to the bottom)
    assert sectors[3]["rank"] is None
    assert sectors[3]["sector"] == "Empty Sector"
    assert sectors[3]["data_quality"] == "INSUFFICIENT_DATA"


def test_missing_classification_handling(monkeypatch):
    """Test engine handling when the classification service fails or returns empty."""
    monkeypatch.setattr("backend.engines.sector_industry_engine.get_sectors", lambda: [])
    monkeypatch.setattr("backend.engines.sector_industry_engine.get_industries", lambda: pd.DataFrame())

    report = run_sector_industry_engine()

    assert report["status"] == "INSUFFICIENT_DATA"
    assert report["sectors_analyzed"] == 0
    assert report["industries_analyzed"] == 0
    assert report["sector_rankings"] == []
    assert report["industry_rankings"] == []


def test_benchmark_unavailable_behavior(monkeypatch):
    """Test the engine correctly passes down UNAVAILABLE when benchmark is missing."""
    monkeypatch.setattr("backend.logic.sector_engine.get_benchmark_historical_data", lambda *args, **kwargs: {"status": "EMPTY", "data": pd.DataFrame()}, raising=False)

    report = run_sector_industry_engine(ranking_period="252D")
    sectors = report["sector_rankings"]

    # Top sector Banking
    banking_sector = sectors[0]
    assert banking_sector["sector"] == "Banking"

    # Validate the documented missing behavior is maintained safely
    rs = banking_sector["relative_strength"]
    assert rs["status"] == "UNAVAILABLE"
    assert rs["252D_rs"] is None
    assert "warning" in rs

def test_incomplete_constituent_data_handling(monkeypatch):
    """Verify missing stock data correctly influences data_quality logic across industries."""
    # Force IT Services to have one valid and one INCOMPLETE stock
    monkeypatch.setattr("backend.logic.sector_engine.get_industry_stocks", lambda i: ["INFY", "INCOMPLETE"] if i == "IT Services" else [])

    report = run_sector_industry_engine(ranking_period="252D")
    industries = report["industry_rankings"]

    # IT Services should now have a PARTIAL data_quality because INCOMPLETE lacks 252D
    it_industry = next((i for i in industries if i["industry"] == "IT Services"), None)

    assert it_industry is not None
    assert it_industry["data_quality"] == "PARTIAL"
    assert "1 constituents" in str(it_industry["warnings"])
