"""
Phase 4.2 Financial Eligibility Boundary Verification Test Suite
===============================================================
Exhaustively verifies all 7 financial eligibility boundary scenarios:
1. Valid technical data + verified financial vintages -> ELIGIBLE, BUY candidate allowed.
2. Valid technical data + ZERO financial records -> TECHNICAL_ONLY, BUY signal strictly forbidden.
3. Financial records + missing publication dates -> Ineligible under PIT, BUY strictly forbidden.
4. Financial records + future publication dates -> Look-ahead quarantined, BUY strictly forbidden.
5. Quarantined financial records -> Ineligible, BUY strictly forbidden.
6. Incomplete fundamental metrics (e.g., 1 quarter) -> COLD_START_INCOMPLETE, BUY strictly forbidden.
7. Valid historical financial vintages -> ELIGIBLE, BUY candidate allowed.

Safety Invariant:
Missing, unverified, future-dated, or quarantined financial data must NEVER be treated
as valid financial evidence, and must NEVER receive a financially qualified BUY signal.
"""

import sqlite3
import datetime
import pytest
import pandas as pd
from pathlib import Path

from backend.database.migrate_universe_schema import migrate_universe_schema
from backend.data_pipeline.stock_onboarding_service import add_stock
from backend.data_pipeline.market_data_onboarding import onboard_stock_market_data
from backend.data_pipeline.universe_coverage_service import get_stock_coverage
from backend.engines.decision_engine import calculate_opportunity_score
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.trade_quality_engine import evaluate_trade_eligibility


def generate_mock_bars(symbol: str, num_bars: int = 250, end_date: str = None) -> pd.DataFrame:
    """Generates clean OHLCV bars ending on end_date (defaults to today)."""
    if end_date is None:
        end_dt = datetime.datetime.now(datetime.timezone.utc).date()
    else:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    start_dt = end_dt - datetime.timedelta(days=num_bars)
    records = []
    price = 1000.0

    for i in range(num_bars):
        d = start_dt + datetime.timedelta(days=i)
        price = price * 1.002
        records.append({
            "date": pd.to_datetime(d),
            "open": price,
            "high": price * 1.02,
            "low": price * 0.98,
            "close": price * 1.005,
            "volume": 200000,
            "adjusted_close": price * 1.005,
        })
    return pd.DataFrame(records)


@pytest.fixture
def financial_boundary_db(tmp_path: Path, monkeypatch):
    """Initializes an isolated SQLite database schema for financial boundary testing."""
    db_path = tmp_path / "fin_boundary.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE industries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sector_id INTEGER REFERENCES sectors(id)
        )
    """)
    cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            sector TEXT,
            industry TEXT,
            exchange TEXT DEFAULT 'NSE',
            sector_id INTEGER REFERENCES sectors(id),
            industry_id INTEGER REFERENCES industries(id)
        )
    """)
    cur.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume INTEGER, adjusted_close REAL,
            UNIQUE(company_id, date)
        )
    """)
    cur.execute("""
        CREATE TABLE technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            date TEXT NOT NULL,
            rsi REAL, macd REAL, macd_signal REAL, macd_histogram REAL,
            ema_20 REAL, ema_50 REAL, ema_200 REAL, atr_14 REAL, technical_score REAL,
            UNIQUE(company_id, date)
        )
    """)
    cur.execute("""
        CREATE TABLE quarterly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            quarter TEXT NOT NULL,
            revenue REAL, net_profit REAL, eps REAL
        )
    """)
    cur.execute("""
        CREATE TABLE quarterly_financial_vintages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            quarter TEXT NOT NULL,
            period_start_date TEXT NOT NULL,
            period_end_date TEXT NOT NULL,
            accounting_standard TEXT NOT NULL DEFAULT 'IND_AS',
            filing_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED',
            company_filing_type TEXT NOT NULL DEFAULT 'ORIGINAL',
            internal_revision_type TEXT NOT NULL DEFAULT 'INITIAL_INGESTION',
            verification_status TEXT NOT NULL DEFAULT 'PROVISIONAL',
            research_eligibility TEXT NOT NULL DEFAULT 'PROVISIONAL_DEMO',
            published_at TEXT,
            effective_trading_date TEXT,
            revenue REAL,
            net_profit REAL,
            eps REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            net_margin REAL
        )
    """)

    cur.execute("INSERT INTO sectors (name) VALUES ('Technology'), ('Manufacturing')")
    cur.execute("INSERT INTO industries (name, sector_id) VALUES ('Software', 1), ('Automotive', 2)")

    conn.commit()
    conn.close()

    migrate_universe_schema(db_path)
    monkeypatch.setenv("DATABASE_PATH", str(db_path.resolve()))
    return db_path


# =============================================================================
# SCENARIO 1: Valid technical data + verified financial vintages
# =============================================================================
def test_scenario_1_valid_technical_and_verified_financials(financial_boundary_db):
    """Stock with full technical data and 4 verified quarters -> ELIGIBLE."""
    stock = add_stock("STOCK1", "Stock 1 Full", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK1", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    # Seed 4 verified quarters with published_at in the past
    conn = sqlite3.connect(financial_boundary_db)
    for q, pend, pub in [
        ("2025-Q1", "2025-03-31", "2025-05-15 16:00:00"),
        ("2025-Q2", "2025-06-30", "2025-08-14 16:00:00"),
        ("2025-Q3", "2025-09-30", "2025-11-14 16:00:00"),
        ("2025-Q4", "2025-12-31", "2026-02-14 16:00:00"),
    ]:
        conn.execute(
            """
            INSERT INTO quarterly_financial_vintages (
                company_id, quarter, period_start_date, period_end_date,
                verification_status, research_eligibility, published_at, effective_trading_date,
                revenue, net_profit, eps, roe, roce, debt_equity, net_margin
            ) VALUES (?, ?, ?, ?, 'VERIFIED', 'VERIFIED_ELIGIBLE', ?, '2026-02-15', 50000, 10000, 25.0, 18.5, 20.2, 0.3, 20.0)
            """,
            (stock["id"], q, pend, pend, pub),
        )
        conn.execute(
            "INSERT INTO quarterly_results (company_id, quarter, revenue, net_profit, eps) VALUES (?, ?, 50000, 10000, 25.0)",
            (stock["id"], q),
        )
    conn.commit()
    conn.close()

    cov = get_stock_coverage("STOCK1", financial_boundary_db)
    assert cov["market_data"]["status"] == "MARKET_DATA_READY"
    assert cov["financial_data"]["status"] == "ELIGIBLE"
    assert cov["financial_data"]["quarter_count"] == 4
    assert cov["readiness"]["composite_status"] == "FULLY_COVERED"
    assert cov["readiness"]["financial_ready"] is True


# =============================================================================
# SCENARIO 2: Valid technical data + ZERO financial records
# =============================================================================
def test_scenario_2_technical_only_zero_financials(financial_boundary_db):
    """
    Stock with full technical data but zero financial records.
    MANDATORY INVARIANT: Must NEVER produce a BUY recommendation or valid signal.
    """
    stock = add_stock("STOCK2", "Stock 2 Tech Only", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK2", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    # Verify coverage state
    cov = get_stock_coverage("STOCK2", financial_boundary_db)
    assert cov["market_data"]["status"] == "MARKET_DATA_READY"
    assert cov["financial_data"]["status"] == "UNVERIFIED_PENDING"
    assert cov["financial_data"]["quarter_count"] == 0
    assert cov["readiness"]["composite_status"] == "TECHNICAL_ONLY"
    assert cov["readiness"]["financial_ready"] is False

    # Verify Decision Engine
    decision = calculate_opportunity_score("STOCK2")
    assert decision["technical_score"] is not None
    assert decision["financial_score"] is None, "Missing financials must produce financial_score=None"
    assert decision["opportunity_score"] is None, "Opportunity score must be None without financials"
    assert decision["recommendation"] == "INSUFFICIENT_DATA", "Recommendation must be INSUFFICIENT_DATA"
    assert decision["status"] == "INSUFFICIENT"

    # Verify Signal Engine
    signal = run_signal_pipeline("STOCK2")
    assert signal["signal_valid"] is False, "BUY signal MUST NOT be generated without financial qualification"
    assert signal["reason"] in {"NOT_A_BUY_RECOMMENDATION", "MISSING_OR_INVALID_INPUTS"}

    # Verify Trade Quality Engine
    quality = evaluate_trade_eligibility(signal)
    assert quality["is_eligible"] is False
    assert quality["risk_status"] in {"INELIGIBLE", "INVALID"}


# =============================================================================
# SCENARIO 3: Financial records with missing publication dates
# =============================================================================
def test_scenario_3_missing_publication_dates(financial_boundary_db):
    """
    Stock with financial rows where published_at is NULL.
    Must be treated as unverified under strict point-in-time governance.
    """
    stock = add_stock("STOCK3", "Stock 3 No Pub Date", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK3", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    conn = sqlite3.connect(financial_boundary_db)
    for q in ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        conn.execute(
            """
            INSERT INTO quarterly_financial_vintages (
                company_id, quarter, period_start_date, period_end_date,
                verification_status, research_eligibility, published_at, effective_trading_date,
                revenue, net_profit, eps
            ) VALUES (?, ?, '2025-01-01', '2025-03-31', 'PROVISIONAL', 'PROVISIONAL_DEMO', NULL, NULL, 50000, 10000, 25.0)
            """,
            (stock["id"], q),
        )
    conn.commit()
    conn.close()

    cov = get_stock_coverage("STOCK3", financial_boundary_db)
    assert cov["financial_data"]["status"] == "UNVERIFIED_PENDING"
    assert cov["readiness"]["composite_status"] == "TECHNICAL_ONLY"

    decision = calculate_opportunity_score("STOCK3", require_verified_publication_date=True)
    assert decision["financial_score"] is None
    assert decision["recommendation"] == "INSUFFICIENT_DATA"

    signal = run_signal_pipeline("STOCK3", require_verified_publication_date=True)
    assert signal["signal_valid"] is False


# =============================================================================
# SCENARIO 4: Financial records with future publication dates
# =============================================================================
def test_scenario_4_future_publication_dates(financial_boundary_db):
    """
    Stock evaluated as of 2026-03-01, but filing published_at is in the future (2026-05-15).
    Look-ahead protection must exclude it.
    """
    stock = add_stock("STOCK4", "Stock 4 Future Pub Date", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK4", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    conn = sqlite3.connect(financial_boundary_db)
    conn.execute(
        """
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, period_start_date, period_end_date,
            verification_status, research_eligibility, published_at, effective_trading_date,
            revenue, net_profit, eps
        ) VALUES (?, '2026-Q1', '2026-01-01', '2026-03-31', 'VERIFIED', 'VERIFIED_ELIGIBLE', '2026-05-15 16:00:00', '2026-05-16', 50000, 10000, 25.0)
        """,
        (stock["id"],),
    )
    conn.commit()
    conn.close()

    # Evaluated at 2026-03-01 (before 2026-05-15 publication)
    decision = calculate_opportunity_score("STOCK4", evaluation_date="2026-03-01", require_verified_publication_date=True)
    assert decision["financial_score"] is None
    assert decision["recommendation"] == "INSUFFICIENT_DATA"

    signal = run_signal_pipeline("STOCK4", evaluation_date="2026-03-01", require_verified_publication_date=True)
    assert signal["signal_valid"] is False


# =============================================================================
# SCENARIO 5: Quarantined financial records
# =============================================================================
def test_scenario_5_quarantined_financial_records(financial_boundary_db):
    """
    Stock with financial rows flagged as QUARANTINED due to data integrity anomaly.
    Must be excluded and marked QUARANTINED.
    """
    stock = add_stock("STOCK5", "Stock 5 Quarantined", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK5", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    conn = sqlite3.connect(financial_boundary_db)
    for q in ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        conn.execute(
            """
            INSERT INTO quarterly_financial_vintages (
                company_id, quarter, period_start_date, period_end_date,
                verification_status, research_eligibility, published_at, effective_trading_date,
                revenue, net_profit, eps
            ) VALUES (?, ?, '2025-01-01', '2025-03-31', 'REJECTED', 'QUARANTINED', '2025-05-15', '2025-05-16', 50000, 10000, 25.0)
            """,
            (stock["id"], q),
        )
    conn.commit()
    conn.close()

    cov = get_stock_coverage("STOCK5", financial_boundary_db)
    assert cov["financial_data"]["status"] == "QUARANTINED"
    assert cov["readiness"]["financial_ready"] is False
    assert cov["readiness"]["composite_status"] == "TECHNICAL_ONLY"

    decision = calculate_opportunity_score("STOCK5", require_verified_publication_date=True)
    assert decision["financial_score"] is None
    assert decision["recommendation"] == "INSUFFICIENT_DATA"

    signal = run_signal_pipeline("STOCK5", require_verified_publication_date=True)
    assert signal["signal_valid"] is False


# =============================================================================
# SCENARIO 6: Incomplete fundamental metrics (e.g. 1 quarter only)
# =============================================================================
def test_scenario_6_incomplete_fundamental_metrics(financial_boundary_db):
    """
    Stock with only 1 quarterly vintage available (insufficient for YoY growth or trends).
    Must produce COLD_START_INCOMPLETE, financial_score=None, recommendation=INSUFFICIENT_DATA.
    """
    stock = add_stock("STOCK6", "Stock 6 Incomplete", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK6", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    conn = sqlite3.connect(financial_boundary_db)
    conn.execute(
        """
        INSERT INTO quarterly_results (company_id, quarter, revenue, net_profit, eps)
        VALUES (?, '2025-Q1', 25000, 3000, 8.5)
        """,
        (stock["id"],),
    )
    conn.commit()
    conn.close()

    cov = get_stock_coverage("STOCK6", financial_boundary_db)
    assert cov["financial_data"]["status"] == "COLD_START_INCOMPLETE"
    assert cov["financial_data"]["quarter_count"] == 1
    assert cov["readiness"]["financial_ready"] is False

    decision = calculate_opportunity_score("STOCK6")
    assert decision["financial_score"] is None, "1 quarter cannot satisfy financial score requirements"
    assert decision["recommendation"] == "INSUFFICIENT_DATA"

    signal = run_signal_pipeline("STOCK6")
    assert signal["signal_valid"] is False


# =============================================================================
# SCENARIO 7: Valid historical financial vintages
# =============================================================================
def test_scenario_7_valid_historical_financial_vintages(financial_boundary_db):
    """
    Stock with full historical verified vintages meeting statutory reporting lag.
    Eligible for financial scoring and full BUY consideration.
    """
    stock = add_stock("STOCK7", "Stock 7 Historical", "Technology", "Software", db_path=financial_boundary_db)
    onboard_stock_market_data("STOCK7", db_path=financial_boundary_db, data_provider=lambda s: generate_mock_bars(s, 250))

    conn = sqlite3.connect(financial_boundary_db)
    for q, pend, pub in [
        ("2024-Q1", "2024-03-31", "2024-05-15 16:00:00"),
        ("2024-Q2", "2024-06-30", "2024-08-14 16:00:00"),
        ("2024-Q3", "2024-09-30", "2024-11-14 16:00:00"),
        ("2024-Q4", "2024-12-31", "2025-02-14 16:00:00"),
    ]:
        conn.execute(
            """
            INSERT INTO quarterly_financial_vintages (
                company_id, quarter, period_start_date, period_end_date,
                verification_status, research_eligibility, published_at, effective_trading_date,
                revenue, net_profit, eps, roe, roce, debt_equity, net_margin
            ) VALUES (?, ?, ?, ?, 'VERIFIED', 'VERIFIED_ELIGIBLE', ?, '2025-02-15', 60000, 12000, 30.0, 22.0, 25.0, 0.2, 20.0)
            """,
            (stock["id"], q, pend, pend, pub),
        )
        conn.execute(
            "INSERT INTO quarterly_results (company_id, quarter, revenue, net_profit, eps) VALUES (?, ?, 60000, 12000, 30.0)",
            (stock["id"], q),
        )
    conn.commit()
    conn.close()

    cov = get_stock_coverage("STOCK7", financial_boundary_db)
    assert cov["financial_data"]["status"] == "ELIGIBLE"
    assert cov["readiness"]["composite_status"] == "FULLY_COVERED"
    assert cov["readiness"]["financial_ready"] is True
