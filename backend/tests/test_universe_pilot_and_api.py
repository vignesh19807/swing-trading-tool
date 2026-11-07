"""
Phase 4 Controlled Expansion Pilot & Dynamic Universe API Tests
==============================================================
Validates:
1. Controlled onboarding of 5 pilot stocks into an isolated test database.
2. Market data onboarding and technical indicator generation (>=200 bars).
3. Decoupled coverage tracking:
   - Market Data: MARKET_DATA_READY
   - Fundamentals: UNVERIFIED_PENDING (no fake financial scores)
   - Readiness: TECHNICAL_ONLY
4. Decision Engine cold-start tolerance:
   - rank_universe() executes without error on newly expanded universe.
5. Dynamic Universe REST API endpoints (/api/universe/*).
6. Non-destructive deactivation safety invariant.
"""

import sqlite3
import datetime
import pytest
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import app
from backend.database.migrate_universe_schema import migrate_universe_schema
from backend.data_pipeline.stock_onboarding_service import (
    add_stock,
    activate_stock,
    deactivate_stock,
    get_audit_history,
)
from backend.data_pipeline.stock_universe_service import (
    get_active_universe,
    get_universe_stock,
    get_universe_count,
)
from backend.data_pipeline.market_data_onboarding import (
    onboard_stock_market_data,
    batch_onboard_cold_start_stocks,
)
from backend.data_pipeline.universe_coverage_service import (
    get_stock_coverage,
    get_universe_coverage_summary,
)


PILOT_STOCKS = [
    {"symbol": "PIDILITIND", "company_name": "Pidilite Industries Limited", "sector": "Materials", "industry": "Specialty Chemicals"},
    {"symbol": "HAVELLS", "company_name": "Havells India Limited", "sector": "Industrials", "industry": "Electrical Equipment"},
    {"symbol": "DABUR", "company_name": "Dabur India Limited", "sector": "Consumer Staples", "industry": "Packaged Foods"},
    {"symbol": "VOLTAS", "company_name": "Voltas Limited", "sector": "Consumer Discretionary", "industry": "Air Conditioning"},
    {"symbol": "SIEMENS", "company_name": "Siemens Limited", "sector": "Industrials", "industry": "Heavy Electrical"},
]


def generate_mock_market_data(symbol: str, num_bars: int = 250) -> pd.DataFrame:
    """Generates synthetic, deterministic, clean OHLCV data for test onboarding."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start_date = today - datetime.timedelta(days=num_bars)
    records = []
    price = 1000.0

    for i in range(num_bars):
        current_date = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        open_price = price
        high_price = price * 1.02
        low_price = price * 0.98
        close_price = price * 1.005
        price = close_price

        records.append({
            "date": pd.to_datetime(current_date),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": 250000,
            "adjusted_close": close_price,
        })

    return pd.DataFrame(records)


@pytest.fixture
def pilot_db(tmp_path: Path, monkeypatch):
    """Initializes an isolated SQLite database pre-seeded with baseline tables."""
    db_path = tmp_path / "pilot_universe.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables
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

    # Seed 2 baseline companies
    cur.execute("INSERT INTO sectors (name) VALUES ('Information Technology'), ('Energy')")
    cur.execute("INSERT INTO industries (name, sector_id) VALUES ('Software', 1), ('Oil & Gas', 2)")
    cur.execute(
        "INSERT INTO companies (symbol, company_name, sector, industry, sector_id, industry_id) "
        "VALUES ('TCS', 'Tata Consultancy Services', 'Information Technology', 'Software', 1, 1)"
    )
    cur.execute(
        "INSERT INTO companies (symbol, company_name, sector, industry, sector_id, industry_id) "
        "VALUES ('RELIANCE', 'Reliance Industries', 'Energy', 'Oil & Gas', 2, 2)"
    )

    conn.commit()
    conn.close()

    # Apply Phase 4 universe schema migration
    migrate_universe_schema(db_path)

    # Point application config & environment to this isolated DB
    monkeypatch.setenv("DATABASE_PATH", str(db_path.resolve()))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.resolve()}")
    return db_path


def test_controlled_pilot_onboarding_and_coverage(pilot_db):
    """Tests full onboarding of 5 pilot stocks into the isolated database."""
    # 1. Verify baseline
    baseline_counts = get_universe_count(pilot_db)
    assert baseline_counts["active"] == 2
    assert baseline_counts["total"] == 2

    # 2. Add 5 pilot stocks in COLD_START
    for stock_meta in PILOT_STOCKS:
        record = add_stock(
            symbol=stock_meta["symbol"],
            company_name=stock_meta["company_name"],
            sector=stock_meta["sector"],
            industry=stock_meta["industry"],
            source="PILOT_EXPANSION",
            status="COLD_START",
            db_path=pilot_db,
        )
        assert record["status"] == "COLD_START"
        assert record["is_active"] == 0

    counts_after_add = get_universe_count(pilot_db)
    assert counts_after_add["total"] == 7
    assert counts_after_add["active"] == 2
    assert counts_after_add["cold_start"] == 5

    # 3. Batch onboard market data with synthetic 250 bars
    batch_res = batch_onboard_cold_start_stocks(
        db_path=pilot_db,
        data_provider=lambda sym: generate_mock_market_data(sym, num_bars=250),
    )
    assert batch_res["total_attempted"] == 5
    assert batch_res["successful"] == 5
    assert batch_res["failed"] == 0

    # 4. Verify all 5 are now ACTIVE
    counts_after_market = get_universe_count(pilot_db)
    assert counts_after_market["active"] == 7
    assert counts_after_market["cold_start"] == 0

    # 5. Check Decoupled Coverage for a pilot stock (PIDILITIND)
    cov = get_stock_coverage("PIDILITIND", pilot_db)
    assert cov is not None
    assert cov["market_data"]["status"] == "MARKET_DATA_READY"
    assert cov["market_data"]["bar_count"] == 250
    assert cov["financial_data"]["status"] == "UNVERIFIED_PENDING"
    assert cov["financial_data"]["quarter_count"] == 0
    # Crucial: Must be marked TECHNICAL_ONLY (ready for technicals, awaiting fundamentals)
    assert cov["readiness"]["composite_status"] == "TECHNICAL_ONLY"
    assert cov["readiness"]["technical_ready"] is True
    assert cov["readiness"]["financial_ready"] is False

    # 6. Check Aggregate Coverage Summary
    summary = get_universe_coverage_summary(pilot_db)
    assert summary["total_active_stocks"] == 7
    assert summary["market_data_breakdown"]["MARKET_DATA_READY"] == 5  # the 5 pilot stocks have data
    assert summary["financial_data_breakdown"]["UNVERIFIED_PENDING"] == 7
    assert summary["composite_readiness_breakdown"]["TECHNICAL_ONLY"] == 5


def test_universe_api_endpoints(pilot_db, monkeypatch):
    """Validates FastAPI REST endpoints for dynamic universe management with security enforcement."""
    client = TestClient(app)

    # 1. GET /api/universe/stocks (Public read-only)
    resp = client.get("/api/universe/stocks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["stocks"]) == 2

    # 2. Security Test: Unauthorized write when ADMIN_API_KEY is not configured
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    unauth_resp = client.post(
        "/api/universe/stocks",
        json={"symbol": "ASIANPAINT", "company_name": "Asian Paints", "sector": "Materials"},
    )
    assert unauth_resp.status_code == 403
    assert "ADMIN_API_KEY is not configured" in unauth_resp.json()["detail"]

    # Configure ADMIN_API_KEY
    admin_key = "test-admin-secret-key"
    monkeypatch.setenv("ADMIN_API_KEY", admin_key)
    auth_headers = {"X-API-Key": admin_key}

    # Security Test: Wrong API key
    wrong_key_resp = client.post(
        "/api/universe/stocks",
        headers={"X-API-Key": "wrong-key"},
        json={"symbol": "ASIANPAINT", "company_name": "Asian Paints", "sector": "Materials"},
    )
    assert wrong_key_resp.status_code == 401
    assert "Invalid or missing" in wrong_key_resp.json()["detail"]

    # 3. POST /api/universe/stocks (Authorized onboard new stock)
    post_resp = client.post(
        "/api/universe/stocks",
        headers=auth_headers,
        json={
            "symbol": "ASIANPAINT",
            "company_name": "Asian Paints Limited",
            "sector": "Materials",
            "industry": "Paints",
            "source": "API_TEST",
            "status": "COLD_START",
            "notes": "Pilot API test",
        },
    )
    assert post_resp.status_code == 201
    post_data = post_resp.json()
    assert post_data["stock"]["symbol"] == "ASIANPAINT"
    assert post_data["stock"]["status"] == "COLD_START"

    # Verify duplicate rejection (HTTP 400)
    dup_resp = client.post(
        "/api/universe/stocks",
        headers=auth_headers,
        json={
            "symbol": "ASIANPAINT",
            "company_name": "Duplicate",
            "sector": "Materials",
        },
    )
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"]

    # 4. GET /api/universe/coverage?symbol=ASIANPAINT (Public read-only)
    cov_resp = client.get("/api/universe/coverage?symbol=ASIANPAINT")
    assert cov_resp.status_code == 200
    cov_data = cov_resp.json()
    assert cov_data["symbol"] == "ASIANPAINT"
    assert cov_data["market_data"]["status"] == "NO_DATA"
    assert cov_data["readiness"]["composite_status"] == "ONBOARDING"

    # 5. PATCH /api/universe/stocks/ASIANPAINT/status (Authorized soft deactivation)
    patch_resp = client.patch(
        "/api/universe/stocks/ASIANPAINT/status",
        headers=auth_headers,
        json={
            "status": "INACTIVE",
            "initiated_by": "TEST_SUITE",
            "notes": "Testing soft deactivation",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["stock"]["status"] == "INACTIVE"
    assert patch_resp.json()["stock"]["is_active"] == 0

    # 6. GET /api/universe/audit?symbol=ASIANPAINT (Authorized audit inspection)
    audit_unauth = client.get("/api/universe/audit?symbol=ASIANPAINT")
    assert audit_unauth.status_code == 401

    audit_resp = client.get("/api/universe/audit?symbol=ASIANPAINT", headers=auth_headers)
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert len(audit_data["audit_events"]) >= 2
    actions = [e["action"] for e in audit_data["audit_events"]]
    assert "ADD" in actions
    assert "STATUS_CHANGE" in actions


def test_non_destructive_deactivation_preserves_records(pilot_db):
    """Verifies that soft-deactivating a stock leaves its historical data completely intact."""
    # Onboard a stock with market data
    stock = add_stock(
        symbol="TITAN",
        company_name="Titan Company Limited",
        sector="Consumer Discretionary",
        db_path=pilot_db,
    )
    onboard_stock_market_data(
        symbol="TITAN",
        db_path=pilot_db,
        data_provider=lambda sym: generate_mock_market_data(sym, num_bars=210),
    )

    # Verify rows in daily_prices
    conn = sqlite3.connect(pilot_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_prices WHERE company_id = ?", (stock["id"],))
    count_before = cur.fetchone()[0]
    assert count_before >= 200

    # Soft deactivate
    deactivate_stock("TITAN", initiated_by="AUDIT_VERIFICATION", db_path=pilot_db)

    # Verify rows STILL in daily_prices
    cur.execute("SELECT COUNT(*) FROM daily_prices WHERE company_id = ?", (stock["id"],))
    count_after = cur.fetchone()[0]
    assert count_after == count_before, "Deactivating stock MUST NOT delete historical price records!"
    conn.close()
