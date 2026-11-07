"""
Test Dynamic Universe Management (Phase 4)
===========================================
Validates:
- Schema migration idempotence.
- Backward compatibility on legacy schema without is_active.
- Symbol validation (NSE formats, rejects .NS/.BO suffixes).
- Onboarding lifecycle: COLD_START -> ACTIVE -> INACTIVE.
- Non-destructive deactivation (preserves price & financial data).
- Audit trail integrity.
"""

import sqlite3
import pytest
from pathlib import Path

from backend.database.migrate_universe_schema import migrate_universe_schema
from backend.data_pipeline.stock_universe_service import (
    get_active_universe,
    get_active_symbols,
    get_universe_stock,
    get_universe_count,
    get_all_universe_stocks,
)
from backend.data_pipeline.stock_onboarding_service import (
    validate_symbol,
    add_stock,
    activate_stock,
    deactivate_stock,
    update_stock_status,
    get_audit_history,
)


@pytest.fixture
def isolated_universe_db(tmp_path: Path):
    """Creates a temporary isolated SQLite database with legacy schema."""
    db_file = tmp_path / "test_universe.db"
    conn = sqlite3.connect(db_file)
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
            open REAL, high REAL, low REAL, close REAL, volume INTEGER,
            UNIQUE(company_id, date)
        )
    """)

    # Seed 3 legacy companies
    cur.execute("INSERT INTO sectors (name) VALUES ('Information Technology'), ('Energy')")
    cur.execute("INSERT INTO industries (name, sector_id) VALUES ('Software', 1), ('Oil & Gas', 2)")
    cur.execute(
        "INSERT INTO companies (symbol, company_name, sector, industry, sector_id, industry_id) "
        "VALUES ('TCS', 'Tata Consultancy Services', 'Information Technology', 'Software', 1, 1)"
    )
    cur.execute(
        "INSERT INTO companies (symbol, company_name, sector, industry, sector_id, industry_id) "
        "VALUES ('INFY', 'Infosys Limited', 'Information Technology', 'Software', 1, 1)"
    )
    cur.execute(
        "INSERT INTO companies (symbol, company_name, sector, industry, sector_id, industry_id) "
        "VALUES ('RELIANCE', 'Reliance Industries Limited', 'Energy', 'Oil & Gas', 2, 2)"
    )

    # Seed a price record for TCS
    cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume) VALUES (1, '2026-01-01', 3500, 3550, 3490, 3540, 100000)")

    conn.commit()
    conn.close()
    return db_file


def test_legacy_schema_fallback(isolated_universe_db):
    """Universe service should operate transparently on an unmigrated database."""
    stocks = get_active_universe(isolated_universe_db)
    assert len(stocks) == 3
    assert [s["symbol"] for s in stocks] == ["INFY", "RELIANCE", "TCS"]
    assert all(s["is_active"] == 1 for s in stocks)
    assert all(s["status"] == "ACTIVE" for s in stocks)

    counts = get_universe_count(isolated_universe_db)
    assert counts["total"] == 3
    assert counts["active"] == 3


def test_schema_migration_idempotence(isolated_universe_db):
    """Migration should apply cleanly and be safely repeatable."""
    assert migrate_universe_schema(isolated_universe_db) is True
    # Run a second time to verify idempotency
    assert migrate_universe_schema(isolated_universe_db) is True

    conn = sqlite3.connect(isolated_universe_db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(companies)")
    cols = {r[1] for r in cur.fetchall()}
    assert {"is_active", "status", "listing_date", "created_at", "updated_at", "source"}.issubset(cols)

    # Check that legacy rows retained active state
    cur.execute("SELECT symbol, is_active, status FROM companies ORDER BY symbol")
    rows = cur.fetchall()
    assert len(rows) == 3
    for sym, is_active, status in rows:
        assert is_active == 1
        assert status == "ACTIVE"
    conn.close()


def test_symbol_validation():
    """Verify symbol normalization and strict format rules."""
    assert validate_symbol("reliance") == "RELIANCE"
    assert validate_symbol("  tcs  ") == "TCS"
    assert validate_symbol("M&M") == "M&M"
    assert validate_symbol("BAJAJ-AUTO") == "BAJAJ-AUTO"

    with pytest.raises(ValueError, match="must not include exchange suffix"):
        validate_symbol("TCS.NS")

    with pytest.raises(ValueError, match="must not include exchange suffix"):
        validate_symbol("RELIANCE.BO")

    with pytest.raises(ValueError, match="Invalid ticker format"):
        validate_symbol("TCS@LTD")

    with pytest.raises(ValueError, match="non-empty string"):
        validate_symbol("")


def test_onboarding_lifecycle_and_non_destructive_deactivation(isolated_universe_db):
    """Test full lifecycle: ADD -> COLD_START -> ACTIVATE -> DEACTIVATE."""
    migrate_universe_schema(isolated_universe_db)

    # 1. Add new stock in COLD_START
    new_stock = add_stock(
        symbol="HDFCBANK",
        company_name="HDFC Bank Limited",
        sector="Financial Services",
        industry="Private Bank",
        source="EXPANSION_PILOT",
        status="COLD_START",
        notes="Onboarding pilot stock",
        db_path=isolated_universe_db,
    )
    assert new_stock["symbol"] == "HDFCBANK"
    assert new_stock["is_active"] == 0
    assert new_stock["status"] == "COLD_START"

    # Active universe should still only be the original 3
    active_stocks = get_active_universe(isolated_universe_db)
    assert len(active_stocks) == 3
    assert "HDFCBANK" not in [s["symbol"] for s in active_stocks]

    counts = get_universe_count(isolated_universe_db)
    assert counts["total"] == 4
    assert counts["active"] == 3
    assert counts["cold_start"] == 1

    # 2. Prevent duplicate addition
    with pytest.raises(ValueError, match="already exists"):
        add_stock(
            symbol="HDFCBANK",
            company_name="Duplicate Bank",
            sector="Financial Services",
            db_path=isolated_universe_db,
        )

    # 3. Activate stock
    activated = activate_stock("HDFCBANK", notes="Market data backfill complete", db_path=isolated_universe_db)
    assert activated["is_active"] == 1
    assert activated["status"] == "ACTIVE"

    active_symbols = get_active_symbols(isolated_universe_db)
    assert len(active_symbols) == 4
    assert "HDFCBANK" in active_symbols

    # Add a mock price row for HDFCBANK
    conn = sqlite3.connect(isolated_universe_db)
    conn.execute(
        "INSERT INTO daily_prices (company_id, date, open, high, low, close, volume) VALUES (?, '2026-01-01', 1600, 1620, 1590, 1610, 500000)",
        (new_stock["id"],),
    )
    conn.commit()
    conn.close()

    # 4. Deactivate stock
    deactivated = deactivate_stock("HDFCBANK", notes="Suspended for testing", db_path=isolated_universe_db)
    assert deactivated["is_active"] == 0
    assert deactivated["status"] == "INACTIVE"

    active_symbols_after = get_active_symbols(isolated_universe_db)
    assert len(active_symbols_after) == 3
    assert "HDFCBANK" not in active_symbols_after

    # CRITICAL: Verify price data was NOT deleted
    conn = sqlite3.connect(isolated_universe_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_prices WHERE company_id = ?", (new_stock["id"],))
    assert cur.fetchone()[0] == 1, "Price data must be preserved when a stock is deactivated!"
    conn.close()

    # 5. Verify Audit Trail
    history = get_audit_history(symbol="HDFCBANK", db_path=isolated_universe_db)
    assert len(history) == 3
    actions = [h["action"] for h in history]
    assert actions == ["DEACTIVATE", "ACTIVATE", "ADD"]

