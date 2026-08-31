"""
Tests for Sector & Industry Intelligence Logic Engine
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from backend.logic.sector_engine import (
    evaluate_sector,
    evaluate_industry,
    rank_sectors,
    rank_industries,
    DEFAULT_LOOKBACK_PERIODS
)

# --------------------------------------------------
# MOCKS
# --------------------------------------------------

def mock_get_company_classification(symbol):
    if symbol == "MISSING_CLASS":
        return None
    return {
        "symbol": symbol,
        "company_name": f"{symbol} Ltd.",
        "sector": "Information Technology",
        "industry": "IT Services"
    }

def mock_get_sector_stocks(sector):
    if sector == "Empty Sector":
        return []
    elif sector == "IT":
        return ["INFY", "TCS"]
    elif sector == "Banking":
        return ["HDFCBANK"]
    elif sector == "Energy":
        return ["RELIANCE"]
    elif sector == "Tie IT":
        return ["INFY", "TCS"]
    return ["INFY", "TCS", "MISSING_CLASS"]

def mock_get_industry_stocks(industry):
    if industry == "Empty Industry":
        return []
    elif industry == "IT Services":
        return ["INFY", "TCS"]
    elif industry == "Private Banks":
        return ["HDFCBANK"]
    elif industry == "Refineries":
        return ["RELIANCE"]
    elif industry == "Tie IT Services":
        return ["INFY", "TCS"]
    return ["INFY", "TCS"]

def create_mock_historical_data(symbol, start_price, end_price, length, has_nan=False, zero_start=False):
    """
    Creates length days of data.
    Prices linearly interpolate from start_price to end_price over length days,
    so that index 0 is start_price, index -1 is end_price.
    If zero_start is True, a specific historical price is 0.0 to test divide-by-zero handling.
    """
    if length <= 0:
        return {
            "status": "EMPTY",
            "data": pd.DataFrame()
        }

    prices = np.linspace(start_price, end_price, length)

    if zero_start and length > 21:
        prices[length - 1 - 21] = 0.0 # Make the 21D ago price 0

    if has_nan and length > 21:
        prices[length - 1 - 21] = np.nan

    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=length, freq="B"),
        "adjusted_close": prices
    })

    return {
        "symbol": symbol,
        "status": "VALID",
        "data": df
    }

def mock_get_historical_data(symbol, start_date=None, end_date=None, include_adjusted_close=True):
    # Depending on symbol, return different mock data

    # INFY: length 300 (has 21D, 63D, 126D, 252D)
    # Let's say 252D ago price = 100, latest = 120 (return = 20%)
    if symbol == "INFY":
        return create_mock_historical_data(symbol, 100, 120, 300)

    # TCS: length 300, 252D ago price = 100, latest = 110 (return = 10%)
    elif symbol == "TCS":
        return create_mock_historical_data(symbol, 100, 110, 300)

    # HDFCBANK: 30% return
    elif symbol == "HDFCBANK":
        return create_mock_historical_data(symbol, 100, 130, 300)

    # RELIANCE: -10% return
    elif symbol == "RELIANCE":
        return create_mock_historical_data(symbol, 100, 90, 300)

    # INSUFFICIENT: length 50 (only has 21D, no 63D, 126D, 252D)
    elif symbol == "INSUFFICIENT":
        return create_mock_historical_data(symbol, 100, 105, 50)

    # ZERO_START: the price 21D ago is 0
    elif symbol == "ZERO_START":
        return create_mock_historical_data(symbol, 100, 120, 100, zero_start=True)

    # HAS_NAN: the price 21D ago is NaN
    elif symbol == "HAS_NAN":
        return create_mock_historical_data(symbol, 100, 120, 100, has_nan=True)

    elif symbol == "MISSING_CLASS":
        # Act like it has no data
        return {"status": "EMPTY", "data": pd.DataFrame()}

    return {"status": "EMPTY", "data": pd.DataFrame()}

def mock_get_benchmark_historical_data(symbol, start_date=None, end_date=None, include_adjusted_close=True):
    if symbol == "NIFTY_50":
        return create_mock_historical_data(symbol, 100, 110, 300)
    elif symbol == "MISSING_BENCHMARK":
        return {"status": "EMPTY", "data": pd.DataFrame()}
    return {"status": "EMPTY", "data": pd.DataFrame()}

# --------------------------------------------------
# FIXTURES
# --------------------------------------------------

@pytest.fixture(autouse=True)
def apply_mocks(monkeypatch):
    monkeypatch.setattr(
        "backend.logic.sector_engine.get_company_classification",
        mock_get_company_classification
    )
    monkeypatch.setattr(
        "backend.logic.sector_engine.get_sector_stocks",
        mock_get_sector_stocks
    )
    monkeypatch.setattr(
        "backend.logic.sector_engine.get_industry_stocks",
        mock_get_industry_stocks
    )
    monkeypatch.setattr(
        "backend.logic.sector_engine.get_historical_data",
        mock_get_historical_data
    )
    monkeypatch.setattr(
        "backend.logic.sector_engine.get_benchmark_historical_data",
        mock_get_benchmark_historical_data,
        raising=False
    )

# --------------------------------------------------
# TESTS
# --------------------------------------------------

def test_evaluate_sector_contract():
    res = evaluate_sector("Information Technology")

    assert res["sector"] == "Information Technology"
    assert "evaluation_date" in res
    assert res["constituents_count"] == 3
    assert res["constituents"] == ["INFY", "TCS", "MISSING_CLASS"]

    # 1. sector constituent retrieval (tested above)
    # 18. output contract keys/types

    assert "performance" in res
    assert "21D" in res["performance"]
    assert "63D" in res["performance"]
    assert "126D" in res["performance"]
    assert "252D" in res["performance"]

    assert "relative_strength" in res
    assert res["relative_strength"]["benchmark"] == "NIFTY_50"
    assert res["relative_strength"]["status"] == "VALID"
    # Because our mock provides the data, 21D_rs is not None
    assert res["relative_strength"]["21D_rs"] is not None

    assert "data_quality" in res
    assert res["data_quality"]["status"] == "PARTIAL" # Because MISSING_CLASS has no data
    assert "MISSING_CLASS" in res["data_quality"]["missing_stocks"]
    assert any("Classification missing" in w for w in res["data_quality"]["warnings"])
    # 16. classification missing data

def test_evaluate_industry_contract():
    # 2. industry constituent retrieval
    res = evaluate_industry("IT Services")
    assert res["industry"] == "IT Services"
    assert res["constituents_count"] == 2
    assert res["constituents"] == ["INFY", "TCS"]
    assert res["data_quality"]["status"] == "VALID" # Both INFY and TCS have full data

def test_historical_return_calculation_and_aggregation():
    # 3. valid historical return calculation
    # 4-7. 21D, 63D, 126D, 252D performance
    # 8. equal-weighted sector aggregation
    # INFY return over 300 days linearly:
    # end = 120, start = 100.
    # period price = 120 - (period/299) * 20
    # TCS return over 300 days linearly:
    # end = 110, start = 100.
    # period price = 110 - (period/299) * 10

    res = evaluate_industry("IT Services") # Uses INFY and TCS

    def expected_ret(period):
        infy_hist = 120 - (period/299)*20
        tcs_hist = 110 - (period/299)*10
        infy_ret = (120 / infy_hist) - 1
        tcs_ret = (110 / tcs_hist) - 1
        return (infy_ret + tcs_ret) / 2

    perf = res["performance"]
    assert perf["21D"] == pytest.approx(expected_ret(21), 1e-4)
    assert perf["63D"] == pytest.approx(expected_ret(63), 1e-4)
    assert perf["126D"] == pytest.approx(expected_ret(126), 1e-4)
    assert perf["252D"] == pytest.approx(expected_ret(252), 1e-4)

def test_insufficient_historical_data(monkeypatch):
    # 10. insufficient historical data
    # 20. multiple constituents with mixed data quality
    monkeypatch.setattr("backend.logic.sector_engine.get_industry_stocks", lambda x: ["INFY", "INSUFFICIENT"])
    res = evaluate_industry("Mixed Industry")

    # INSUFFICIENT has length 50, so it has 21D data, but no 63D, 126D, 252D.
    # INFY has all.
    perf = res["performance"]

    # 21D should be average of INFY and INSUFFICIENT
    assert perf["21D"] is not None
    # 63D should be just INFY, because INSUFFICIENT is excluded, not converted to 0
    # 19. no conversion of missing data to zero
    infy_hist_63 = 120 - (63/299)*20
    infy_ret_63 = (120 / infy_hist_63) - 1
    assert perf["63D"] == pytest.approx(infy_ret_63, 1e-4)

    assert res["data_quality"]["status"] == "PARTIAL"

def test_invalid_nan_prices(monkeypatch):
    # 11. invalid/NaN prices
    monkeypatch.setattr("backend.logic.sector_engine.get_industry_stocks", lambda x: ["HAS_NAN"])
    res = evaluate_industry("NaN Industry")

    perf = res["performance"]
    # 21D has NaN price, so it should be skipped
    assert perf["21D"] is None
    # 63D should be fine
    assert perf["63D"] is not None

def test_zero_starting_price(monkeypatch):
    # 12. zero starting price
    monkeypatch.setattr("backend.logic.sector_engine.get_industry_stocks", lambda x: ["ZERO_START"])
    res = evaluate_industry("Zero Industry")

    perf = res["performance"]
    # 21D has 0.0 price, so it should be skipped (handled without crash)
    assert perf["21D"] is None
    # 63D should be fine
    assert perf["63D"] is not None

def test_empty_sector_and_industry():
    # 14. empty sector
    # 15. empty industry
    # 9. missing stock data
    res_sec = evaluate_sector("Empty Sector")
    assert res_sec["constituents_count"] == 0
    assert res_sec["data_quality"]["status"] == "INSUFFICIENT_DATA"
    assert res_sec["performance"]["21D"] is None

    res_ind = evaluate_industry("Empty Industry")
    assert res_ind["constituents_count"] == 0
    assert res_ind["data_quality"]["status"] == "INSUFFICIENT_DATA"
    assert res_ind["performance"]["252D"] is None

def test_evaluation_date_determinism(monkeypatch):
    # 13. evaluation_date determinism
    # If we pass evaluation_date, it is passed to get_historical_data
    # We can mock get_historical_data to assert the end_date passed is evaluation_date
    called_with_end_date = []
    def spy_get_historical_data(symbol, start_date=None, end_date=None, include_adjusted_close=True):
        called_with_end_date.append(end_date)
        return {"status": "EMPTY", "data": pd.DataFrame()}

    monkeypatch.setattr("backend.logic.sector_engine.get_historical_data", spy_get_historical_data)
    evaluate_sector("Information Technology", evaluation_date="2025-08-31")

    assert all(date == "2025-08-31" for date in called_with_end_date)


def test_rank_sectors_basic():
    # IT -> 15% (INFY 20%, TCS 10%)
    # Banking -> 30%
    # Energy -> -10%
    sectors = ["Energy", "IT", "Banking"]
    res = rank_sectors(sectors, ranking_period="252D")

    assert res["ranking_period"] == "252D"
    ranked = res["ranked_sectors"]
    assert len(ranked) == 3

    hdfc_hist_252 = 130 - (252/299) * 30
    hdfc_ret_252 = (130 / hdfc_hist_252) - 1

    infy_hist_252 = 120 - (252/299) * 20
    tcs_hist_252 = 110 - (252/299) * 10
    it_ret_252 = ((120 / infy_hist_252 - 1) + (110 / tcs_hist_252 - 1)) / 2

    reliance_hist_252 = 90 - (252/299) * (-10)
    reliance_ret_252 = (90 / reliance_hist_252) - 1

    # 1: Banking, 2: IT, 3: Energy
    assert ranked[0]["rank"] == 1
    assert ranked[0]["sector"] == "Banking"
    assert ranked[0]["performance"] == pytest.approx(hdfc_ret_252, 1e-4)

    assert ranked[1]["rank"] == 2
    assert ranked[1]["sector"] == "IT"
    assert ranked[1]["performance"] == pytest.approx(it_ret_252, 1e-4)

    assert ranked[2]["rank"] == 3
    assert ranked[2]["sector"] == "Energy"
    assert ranked[2]["performance"] == pytest.approx(reliance_ret_252, 1e-4)

def test_rank_sectors_ties():
    # IT and Tie IT both have INFY and TCS (15% return)
    # Energy is -10%
    sectors = ["Energy", "IT", "Tie IT"]
    res = rank_sectors(sectors, ranking_period="252D")

    ranked = res["ranked_sectors"]
    # Tie broken alphabetically: IT before Tie IT
    assert ranked[0]["sector"] == "IT"
    assert ranked[1]["sector"] == "Tie IT"
    assert ranked[2]["sector"] == "Energy"

def test_rank_sectors_incomplete():
    # Empty Sector has None performance
    sectors = ["Empty Sector", "IT"]
    res = rank_sectors(sectors, ranking_period="252D")

    ranked = res["ranked_sectors"]
    assert len(ranked) == 2

    assert ranked[0]["rank"] == 1
    assert ranked[0]["sector"] == "IT"

    assert ranked[1]["rank"] is None
    assert ranked[1]["sector"] == "Empty Sector"
    assert ranked[1]["performance"] is None
    assert ranked[1]["data_quality"] == "INSUFFICIENT_DATA"


def test_rank_industries_basic():
    industries = ["Refineries", "IT Services", "Private Banks"]
    res = rank_industries(industries, ranking_period="252D")

    assert res["ranking_period"] == "252D"
    ranked = res["ranked_industries"]
    assert len(ranked) == 3

    hdfc_hist_252 = 130 - (252/299) * 30
    hdfc_ret_252 = (130 / hdfc_hist_252) - 1

    infy_hist_252 = 120 - (252/299) * 20
    tcs_hist_252 = 110 - (252/299) * 10
    it_ret_252 = ((120 / infy_hist_252 - 1) + (110 / tcs_hist_252 - 1)) / 2

    reliance_hist_252 = 90 - (252/299) * (-10)
    reliance_ret_252 = (90 / reliance_hist_252) - 1

    assert ranked[0]["rank"] == 1
    assert ranked[0]["industry"] == "Private Banks"
    assert ranked[0]["performance"] == pytest.approx(hdfc_ret_252, 1e-4)

    assert ranked[1]["rank"] == 2
    assert ranked[1]["industry"] == "IT Services"
    assert ranked[1]["performance"] == pytest.approx(it_ret_252, 1e-4)

    assert ranked[2]["rank"] == 3
    assert ranked[2]["industry"] == "Refineries"
    assert ranked[2]["performance"] == pytest.approx(reliance_ret_252, 1e-4)

def test_rank_industries_ties():
    industries = ["Refineries", "IT Services", "Tie IT Services"]
    res = rank_industries(industries, ranking_period="252D")

    ranked = res["ranked_industries"]
    assert ranked[0]["industry"] == "IT Services"
    assert ranked[1]["industry"] == "Tie IT Services"
    assert ranked[2]["industry"] == "Refineries"

def test_rank_industries_incomplete():
    industries = ["Empty Industry", "IT Services"]
    res = rank_industries(industries, ranking_period="252D")

    ranked = res["ranked_industries"]
    assert len(ranked) == 2

    assert ranked[0]["rank"] == 1
    assert ranked[0]["industry"] == "IT Services"

    assert ranked[1]["rank"] is None
    assert ranked[1]["industry"] == "Empty Industry"
    assert ranked[1]["performance"] is None
    assert ranked[1]["data_quality"] == "INSUFFICIENT_DATA"

def test_relative_strength_and_sector_score():
    res = evaluate_sector("Information Technology") # INFY + TCS

    # IT return = ~15%, benchmark = ~10% -> RS is ~5%
    infy_hist_252 = 120 - (252/299) * 20
    tcs_hist_252 = 110 - (252/299) * 10
    it_ret_252 = ((120 / infy_hist_252 - 1) + (110 / tcs_hist_252 - 1)) / 2

    bench_hist_252 = 110 - (252/299) * 10
    bench_ret_252 = (110 / bench_hist_252) - 1

    rs_252 = it_ret_252 - bench_ret_252

    assert res["relative_strength"]["status"] == "VALID"
    assert res["relative_strength"]["252D_rs"] == pytest.approx(rs_252, 1e-4)

    # Outperformance (Banking vs Benchmark)
    res_bank = evaluate_sector("Banking") # HDFCBANK: ~30%
    assert res_bank["relative_strength"]["status"] == "VALID"
    assert res_bank["relative_strength"]["252D_rs"] > 0

    # Underperformance (Energy vs Benchmark)
    res_energy = evaluate_sector("Energy") # RELIANCE: ~-10%
    assert res_energy["relative_strength"]["status"] == "VALID"
    assert res_energy["relative_strength"]["252D_rs"] < 0

    # Score checks
    score_data = res["preliminary_score"]
    assert score_data["range"]["min"] == 0.0
    assert score_data["range"]["max"] == 100.0
    assert score_data["score"] is not None
    assert 0.0 <= score_data["score"] <= 100.0
    assert "21D_component" in score_data["components"]
    assert "63D_component" in score_data["components"]

def test_missing_benchmark(monkeypatch):
    monkeypatch.setattr("backend.logic.sector_engine.get_benchmark_historical_data", lambda *args, **kwargs: {"status": "EMPTY", "data": pd.DataFrame()}, raising=False)
    res = evaluate_sector("Information Technology")
    assert res["relative_strength"]["status"] == "UNAVAILABLE"
    assert res["relative_strength"]["252D_rs"] is None
    assert res["relative_strength"]["warning"] == "Benchmark data unavailable for calculation."

def test_missing_sector_data_for_rs():
    res = evaluate_sector("Empty Sector")
    assert res["relative_strength"]["status"] == "UNAVAILABLE"
    assert res["relative_strength"]["252D_rs"] is None

def test_score_bounds(monkeypatch):
    # If a sector has massive positive returns, score is clamped to 100.
    def mock_massive(*args, **kwargs):
        return {"21D": 1.0, "63D": 1.0, "126D": 1.0, "252D": 1.0} # 100% return
    monkeypatch.setattr("backend.logic.sector_engine._calculate_constituent_returns", mock_massive)
    res = evaluate_sector("Banking")

    assert res["preliminary_score"]["score"] == 100.0
    assert res["preliminary_score"]["components"]["21D_component"] == 25.0
    assert res["preliminary_score"]["components"]["63D_component"] == 25.0

    # If a sector has massive negative returns, score is clamped to 0.
    def mock_terrible(*args, **kwargs):
        return {"21D": -0.9, "63D": -0.9, "126D": -0.9, "252D": -0.9} # -90% return
    monkeypatch.setattr("backend.logic.sector_engine._calculate_constituent_returns", mock_terrible)
    res = evaluate_sector("Banking")

    assert res["preliminary_score"]["score"] == 0.0
    assert res["preliminary_score"]["components"]["21D_component"] == -25.0
    assert res["preliminary_score"]["components"]["63D_component"] == -25.0
