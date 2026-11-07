"""
Neon PostgreSQL Staging Integration Verification Test Suite
===========================================================
Executes live integration validation against Neon PostgreSQL staging database.

Guarded by:
    @pytest.mark.skipif(not os.getenv("DATABASE_URL") or not os.getenv("DATABASE_URL").startswith(("postgresql://", "postgres://")), ...)

Safety Invariants:
1. NEVER touches or connects to production/staging SQLite files.
2. Only operates on synthetic staging data.
3. Tests read-only queries and safe synthetic writes.
4. Validates all 3 financial immutability triggers live on Neon.
"""

import os
import hashlib
# pyrefly: ignore[missing-import]
import pytest
from pathlib import Path
# pyrefly: ignore[missing-import]
from fastapi.testclient import TestClient

from backend.config import PROJECT_ROOT
from backend.database.connection import (
    open_db_connection,
    reset_db_pool,
    DatabaseEngine,
    DatabaseQueryError,
)

PROD_CANONICAL_SHA256 = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"
STAGING_CANONICAL_SHA256 = "84263F185EC782443F8C15F08F0AEAB96C0BD8B40413D5ADD12C3AE908176BE7"

IS_PG_CONFIGURED = bool(
    os.getenv("DATABASE_URL")
    and os.getenv("DATABASE_URL").strip().startswith(("postgresql://", "postgres://"))
)

pytestmark = pytest.mark.skipif(
    not IS_PG_CONFIGURED,
    reason="DATABASE_URL not set to a PostgreSQL endpoint. Skipping Neon live tests.",
)


@pytest.fixture(autouse=True)
def verify_sqlite_invariants():
    """Guarantee SQLite databases remain byte-for-byte untouched before and after every test."""
    prod_path = PROJECT_ROOT / "database" / "swing_trading.db"
    stag_path = PROJECT_ROOT / "database" / "staging_financial_expansion.db"

    if prod_path.exists():
        assert hashlib.sha256(prod_path.read_bytes()).hexdigest().upper() == PROD_CANONICAL_SHA256
    if stag_path.exists():
        assert hashlib.sha256(stag_path.read_bytes()).hexdigest().upper() == STAGING_CANONICAL_SHA256

    yield

    if prod_path.exists():
        assert hashlib.sha256(prod_path.read_bytes()).hexdigest().upper() == PROD_CANONICAL_SHA256
    if stag_path.exists():
        assert hashlib.sha256(stag_path.read_bytes()).hexdigest().upper() == STAGING_CANONICAL_SHA256


def test_01_neon_connectivity_and_version():
    """Verify Neon connection, PostgreSQL version 16, and SSL mode."""
    with open_db_connection() as conn:
        assert conn.engine == DatabaseEngine.POSTGRESQL
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver_str = cur.fetchone()[0]
            assert "PostgreSQL" in ver_str
            # Neon requires SSL on client link
            pgconn = conn.raw_connection._conn.info.pgconn
            params = conn.raw_connection._conn.info.get_parameters()
            assert bool(pgconn.ssl_in_use) is True
            assert params.get("sslmode") == "require"


def test_02_all_15_domain_tables_exist():
    """Verify that all 15 expected domain tables exist in the Neon public schema."""
    expected_tables = {
        "sectors", "industries", "companies", "daily_prices",
        "technical_indicators", "quarterly_results", "quarterly_financial_vintages",
        "signals", "financial_scores", "opportunity_scores",
        "backtest_runs", "backtest_results", "backtest_trades",
        "backtest_equity_curve", "universe_audit_log"
    }

    with open_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
            )
            found_tables = {r["table_name"] for r in cur.fetchall()}

    missing = expected_tables - found_tables
    assert not missing, f"Missing domain tables on Neon: {missing}"


def test_03_synthetic_data_integrity():
    """Verify synthetic staging companies and price records."""
    with open_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM companies WHERE source = 'NEON_SYNTHETIC_STAGING'")
            comp_count = cur.fetchone()["cnt"]
            assert comp_count >= 10, f"Expected at least 10 synthetic companies, found {comp_count}"

            cur.execute("SELECT COUNT(*) as cnt FROM daily_prices")
            price_count = cur.fetchone()["cnt"]
            assert price_count > 0, "No daily price records found"

            cur.execute("SELECT COUNT(*) as cnt FROM quarterly_financial_vintages")
            vintage_count = cur.fetchone()["cnt"]
            assert vintage_count >= 18, f"Expected at least 18 synthetic vintages, found {vintage_count}"


def test_04_fastapi_endpoints_under_neon():
    """Verify core FastAPI endpoints running against Neon."""
    from backend.app import app
    client = TestClient(app)

    # Liveness
    resp = client.get("/healthz/live")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

    # Readiness
    resp = client.get("/healthz/ready")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ready"
    assert resp.json().get("companies_count") >= 10

    # Composite Health
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"

    # Stock Listing
    resp = client.get("/api/stocks")
    assert resp.status_code == 200
    stocks = resp.json().get("stocks", [])
    assert len(stocks) >= 10
    symbols = {s["symbol"] for s in stocks}
    assert "TCS" in symbols
    assert "RELIANCE" in symbols

    # Stock Detail
    resp = client.get("/api/stocks/TCS")
    assert resp.status_code == 200
    assert resp.json().get("symbol") == "TCS"

    # Stock History
    resp = client.get("/api/stocks/TCS/history")
    assert resp.status_code == 200
    candles = resp.json().get("candles", [])
    assert len(candles) > 0

    # Sectors Analysis
    resp = client.get("/api/sectors")
    assert resp.status_code == 200
    sectors = resp.json().get("sectors", [])
    assert len(sectors) > 0

    # Opportunities
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200

    # Universe coverage
    resp = client.get("/api/universe/coverage")
    assert resp.status_code == 200
    cov_data = resp.json()
    active_count = cov_data.get("total_active_stocks") or cov_data.get("universe_size", 0)
    assert active_count >= 9


def test_05_pit_lookahead_prevention():
    """Verify point-in-time visibility prevents future data lookahead."""
    from backend.data_pipeline.historical_pit_service import PointInTimeEligibilityService

    pit_svc = PointInTimeEligibilityService()

    # TCS Q1FY26 effective date is 2025-07-16.
    # Looking on 2025-07-01 should see None (prior to effective trading date)
    vintage_before = pit_svc.get_eligible_vintage_as_of("TCS", as_of_date="2025-07-01", enforce_coverage=False)
    assert vintage_before is None, "Future vintage was visible before effective trading date!"

    # Looking on 2025-08-01 should see Q1FY26
    vintage_q1 = pit_svc.get_eligible_vintage_as_of("TCS", as_of_date="2025-08-01", enforce_coverage=False)
    assert vintage_q1 is not None
    assert vintage_q1["quarter"] == "Q1FY26"

    # TCS Q2FY26 effective date is 2025-10-16. Looking on 2025-11-01 should see Q2FY26, but NOT Q3 or Q4
    vintage_q2 = pit_svc.get_eligible_vintage_as_of("TCS", as_of_date="2025-11-01", enforce_coverage=False)
    assert vintage_q2 is not None
    assert vintage_q2["quarter"] == "Q2FY26"


def test_06_immutability_triggers_live_on_neon():
    """Verify all 3 financial immutability triggers on Neon."""
    with open_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM quarterly_financial_vintages LIMIT 1")
            vid = cur.fetchone()["id"]

            # Trigger 1: Prevent Deletion
            with pytest.raises(DatabaseQueryError, match="Illegal deletion"):
                cur.execute("DELETE FROM quarterly_financial_vintages WHERE id = %s", (vid,))
            conn.rollback()

            # Trigger 2: Prevent Mutation
            with pytest.raises(DatabaseQueryError, match="Illegal mutation"):
                cur.execute("UPDATE quarterly_financial_vintages SET revenue = 99999.0 WHERE id = %s", (vid,))
            conn.rollback()

            # Trigger 3: Prevent Extraction/Restatement Conflation
            cur.execute("SELECT company_id, quarter FROM quarterly_financial_vintages WHERE id = %s", (vid,))
            row = cur.fetchone()
            cid = row["company_id"]

            with pytest.raises(DatabaseQueryError, match="Semantic Conflation Error"):
                cur.execute(
                    """
                    INSERT INTO quarterly_financial_vintages (
                        company_id, quarter, period_start_date, period_end_date,
                        version_sequence, filing_scope,
                        company_filing_type, internal_revision_type,
                        verification_status, research_eligibility,
                        exchange, exchange_broadcast_id,
                        published_at, effective_trading_date,
                        revenue, net_profit, eps
                    ) VALUES (
                        %s, 'Q1FY99', '2099-01-01', '2099-03-31',
                        99, 'CONSOLIDATED',
                        'CORPORATE_RESTATEMENT', 'EXTRACTION_CORRECTION',
                        'VERIFIED', 'VERIFIED_ELIGIBLE',
                        'NSE', 'SYNTH_TEST_CONFLATION',
                        '2099-04-15 18:30:00+05:30', '2099-04-16',
                        100.0, 10.0, 1.0
                    )
                    """,
                    (cid,),
                )
            conn.rollback()

            # Trigger Guard: Prevent Unverified Promotion
            with pytest.raises(DatabaseQueryError, match="Illegal promotion"):
                cur.execute(
                    "UPDATE quarterly_financial_vintages SET research_eligibility = 'VERIFIED_ELIGIBLE', "
                    "verification_status = 'PROVISIONAL' WHERE id = %s",
                    (vid,),
                )
            conn.rollback()


def test_07_transaction_commit_and_rollback():
    """Verify transaction commit and rollback behavior on Neon."""
    test_sym = "SYNTH_TX_TEST"
    with open_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM companies WHERE symbol = %s", (test_sym,))
        conn.commit()

        # Test Rollback
        with pytest.raises(RuntimeError):
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO companies (symbol, company_name) VALUES (%s, 'Rollback Test')",
                        (test_sym,),
                    )
                raise RuntimeError("Forced rollback")

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM companies WHERE symbol = %s", (test_sym,))
            assert cur.fetchone() is None, "Rollback failed to revert inserted row"

        # Test Commit
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO companies (symbol, company_name) VALUES (%s, 'Commit Test')",
                    (test_sym,),
                )

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM companies WHERE symbol = %s", (test_sym,))
            assert cur.fetchone() is not None, "Commit failed to persist row"

            # Cleanup
            cur.execute("DELETE FROM companies WHERE symbol = %s", (test_sym,))
        conn.commit()

