"""
Week 15 - Automated Data Quality Monitoring System
===================================================

Single reusable Data Quality entry point for the Swing Trading Intelligence Platform.
Performs comprehensive recurring audits across the database layer and classifies
findings into PASS, WARNING, or BLOCKING FAILURE.

Quality Audit Rules:
1. 100-Stock Universe Integrity (Hard Invariant: 50 distinct symbols, 0 missing)
2. Market Data Coverage & Dynamic Date Range (All 50 stocks covered, 0 missing)
3. Technical Indicator Coverage & 1:1 Synchronization (0 unmatched rows)
4. Financial Data Coverage & Upstream Completeness (100/100 companies covered; ROE/ROCE limits as Warning)
5. Sector and Industry Mapping Integrity (0 unmapped companies)
6. Duplicate Record Prevention (0 duplicate groups across all tables)
7. Zero-Volume & Anomaly Detection (Classified as Warning for operational inspection)
8. Foreign Key & Orphan Row Integrity (0 orphan records)
9. Point-in-Time Historical Safety (Validates get_backtest_inputs contract: reporting_period <= evaluation_date)

Data Engineer boundary:
- Performs data quality verification and monitoring.
- Does not modify or calculate trading signals/scores.
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.backtest_data_access_service import get_backtest_inputs

DATABASE_PATH = PROJECT_ROOT / "database" / "swing_trading.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


class Week15QualityMonitor:
    """
    Automated data quality monitoring and audit runner.
    """

    REPRESENTATIVE_SYMBOLS = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC"]

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.results: Dict[str, Any] = {}
        self.blocking_failures: List[str] = []
        self.warnings: List[str] = []

    def get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        return sqlite3.connect(self.db_path)

    # ------------------------------------------------------------
    # 1. 100-Stock Universe Integrity
    # ------------------------------------------------------------
    def check_universe_integrity(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        company_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        distinct_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM companies").fetchone()[0]
        missing_symbols = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE symbol IS NULL OR TRIM(symbol) = ''"
        ).fetchone()[0]

        status = "PASS"
        if company_count != 100 or distinct_symbols != 100 or missing_symbols > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Universe integrity failed: count={company_count}, distinct={distinct_symbols}, missing={missing_symbols}"
            )

        return {
            "check": "Universe Integrity",
            "status": status,
            "company_count": company_count,
            "distinct_symbols": distinct_symbols,
            "missing_symbols": missing_symbols,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 2. Market Data Coverage & Dynamic Range
    # ------------------------------------------------------------
    def check_market_data_coverage(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        total_rows = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
        distinct_companies = conn.execute("SELECT COUNT(DISTINCT company_id) FROM daily_prices").fetchone()[0]
        date_range = conn.execute("SELECT MIN(date), MAX(date) FROM daily_prices").fetchone()
        
        missing_companies = conn.execute(
            """
            SELECT c.symbol
            FROM companies c
            LEFT JOIN daily_prices dp ON c.id = dp.company_id
            WHERE dp.company_id IS NULL
            """
        ).fetchall()

        min_date_str = str(date_range[0])[:10] if date_range[0] else None
        max_date_str = str(date_range[1])[:10] if date_range[1] else None

        status = "PASS"
        if distinct_companies < 100 or len(missing_companies) > 0 or total_rows == 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Market data coverage failure: covered={distinct_companies}/50, total_rows={total_rows}"
            )

        return {
            "check": "Market Data Coverage",
            "status": status,
            "total_rows": total_rows,
            "covered_companies": distinct_companies,
            "min_date": min_date_str,
            "max_date": max_date_str,
            "missing_companies": [r[0] for r in missing_companies],
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 3. Technical Indicators & 1:1 Synchronization
    # ------------------------------------------------------------
    def check_technical_synchronization(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        tech_rows = conn.execute("SELECT COUNT(*) FROM technical_indicators").fetchone()[0]
        
        unmatched_daily = conn.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices d
            LEFT JOIN technical_indicators t
                ON d.company_id = t.company_id AND date(d.date) = date(t.date)
            WHERE t.id IS NULL
            """
        ).fetchone()[0]

        unmatched_tech = conn.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators t
            LEFT JOIN daily_prices d
                ON t.company_id = d.company_id AND date(t.date) = date(d.date)
            WHERE d.id IS NULL
            """
        ).fetchone()[0]

        status = "PASS"
        if unmatched_daily > 0 or unmatched_tech > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Market/Technical synchronization failed: unmatched_daily={unmatched_daily}, unmatched_tech={unmatched_tech}"
            )

        return {
            "check": "Technical Indicator Synchronization",
            "status": status,
            "technical_rows": tech_rows,
            "unmatched_daily_rows": unmatched_daily,
            "unmatched_technical_rows": unmatched_tech,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 4. Financial Data Availability & Completeness
    # ------------------------------------------------------------
    def check_financial_data(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        total_records = conn.execute("SELECT COUNT(*) FROM quarterly_results").fetchone()[0]
        covered_companies = conn.execute("SELECT COUNT(DISTINCT company_id) FROM quarterly_results").fetchone()[0]
        period_range = conn.execute("SELECT MIN(quarter), MAX(quarter) FROM quarterly_results").fetchone()

        missing_companies = conn.execute(
            """
            SELECT c.symbol
            FROM companies c
            LEFT JOIN quarterly_results qr ON c.id = qr.company_id
            WHERE qr.company_id IS NULL
            """
        ).fetchall()

        # Check metric nulls
        metrics = ["revenue", "net_profit", "eps", "roe", "roce", "debt_equity", "operating_margin", "net_margin"]
        metric_nulls = {}
        for m in metrics:
            null_count = conn.execute(
                f"SELECT COUNT(*) FROM quarterly_results WHERE {m} IS NULL"
            ).fetchone()[0]
            metric_nulls[m] = null_count

        status = "PASS"
        if covered_companies < 100 or len(missing_companies) > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Financial coverage failure: covered={covered_companies}/50, missing={missing_companies}"
            )
        elif metric_nulls.get("roe", 0) > 0 or metric_nulls.get("roce", 0) > 0:
            # Known upstream ROE/ROCE limitation is a WARNING, not blocking
            status = "WARNING"
            self.warnings.append(
                f"Upstream financial metric incompleteness: roe_nulls={metric_nulls.get('roe')}, roce_nulls={metric_nulls.get('roce')} (Preserved as known limitation)"
            )

        return {
            "check": "Financial Data Coverage & Completeness",
            "status": status,
            "total_records": total_records,
            "covered_companies": covered_companies,
            "first_quarter": period_range[0],
            "last_quarter": period_range[1],
            "metric_null_counts": metric_nulls,
            "missing_companies": [r[0] for r in missing_companies],
            "passed": status in ["PASS", "WARNING"],
        }

    # ------------------------------------------------------------
    # 5. Sector and Industry Mapping Integrity
    # ------------------------------------------------------------
    def check_classification_mappings(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        sector_count = conn.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
        industry_count = conn.execute("SELECT COUNT(*) FROM industries").fetchone()[0]

        unmapped_sector = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE sector_id IS NULL"
        ).fetchone()[0]

        unmapped_industry = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE industry_id IS NULL"
        ).fetchone()[0]

        status = "PASS"
        if sector_count == 0 or industry_count == 0 or unmapped_sector > 0 or unmapped_industry > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Classification mapping failure: unmapped_sector={unmapped_sector}, unmapped_industry={unmapped_industry}"
            )

        return {
            "check": "Sector & Industry Mappings",
            "status": status,
            "sector_count": sector_count,
            "industry_count": industry_count,
            "unmapped_sector_companies": unmapped_sector,
            "unmapped_industry_companies": unmapped_industry,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 6. Duplicate Records Detection
    # ------------------------------------------------------------
    def check_duplicate_records(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        price_dups = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT company_id, date FROM daily_prices GROUP BY company_id, date HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        tech_dups = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT company_id, date FROM technical_indicators GROUP BY company_id, date HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        fin_dups = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT company_id, quarter FROM quarterly_results GROUP BY company_id, quarter HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        bt_dups = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT run_id, symbol, evaluation_date FROM backtest_results GROUP BY run_id, symbol, evaluation_date HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        total_dups = price_dups + tech_dups + fin_dups + bt_dups
        status = "PASS"
        if total_dups > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Duplicates detected: daily_prices={price_dups}, technical={tech_dups}, financial={fin_dups}, backtest={bt_dups}"
            )

        return {
            "check": "Duplicate Record Detection",
            "status": status,
            "daily_prices_duplicates": price_dups,
            "technical_indicators_duplicates": tech_dups,
            "quarterly_results_duplicates": fin_dups,
            "backtest_results_duplicates": bt_dups,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 7. Zero-Volume & Market Anomaly Detection (Warnings)
    # ------------------------------------------------------------
    def check_market_anomalies(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        invalid_prices = conn.execute(
            """
            SELECT COUNT(*) FROM daily_prices
            WHERE open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 OR volume < 0
            """
        ).fetchone()[0]

        zero_volume_rows = conn.execute(
            "SELECT COUNT(*) FROM daily_prices WHERE volume = 0"
        ).fetchone()[0]

        extreme_moves = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT company_id, date, close,
                       LAG(close) OVER (PARTITION BY company_id ORDER BY date) AS prev_close
                FROM daily_prices
            )
            WHERE prev_close > 0 AND ABS((close - prev_close) / prev_close) > 0.20
            """
        ).fetchone()[0]

        status = "PASS"
        if invalid_prices > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(f"Invalid negative/zero price rows: {invalid_prices}")
        elif zero_volume_rows > 0 or extreme_moves > 0:
            status = "WARNING"
            if zero_volume_rows > 0:
                self.warnings.append(f"Zero-volume trading days detected: {zero_volume_rows} rows (Operational Warning)")
            if extreme_moves > 0:
                self.warnings.append(f"Extreme price moves (>20%): {extreme_moves} rows (Operational Warning)")

        return {
            "check": "Market Value & Volume Anomalies",
            "status": status,
            "invalid_price_rows": invalid_prices,
            "zero_volume_rows": zero_volume_rows,
            "extreme_move_rows": extreme_moves,
            "passed": status in ["PASS", "WARNING"],
        }

    # ------------------------------------------------------------
    # 8. Foreign Key & Orphan Row Integrity
    # ------------------------------------------------------------
    def check_orphan_records(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        market_orphans = conn.execute(
            "SELECT COUNT(*) FROM daily_prices dp LEFT JOIN companies c ON dp.company_id = c.id WHERE c.id IS NULL"
        ).fetchone()[0]

        tech_orphans = conn.execute(
            "SELECT COUNT(*) FROM technical_indicators ti LEFT JOIN companies c ON ti.company_id = c.id WHERE c.id IS NULL"
        ).fetchone()[0]

        fin_orphans = conn.execute(
            "SELECT COUNT(*) FROM quarterly_results qr LEFT JOIN companies c ON qr.company_id = c.id WHERE c.id IS NULL"
        ).fetchone()[0]

        total_orphans = market_orphans + tech_orphans + fin_orphans
        status = "PASS"
        if total_orphans > 0:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Orphan rows detected: market={market_orphans}, tech={tech_orphans}, financial={fin_orphans}"
            )

        return {
            "check": "Foreign Key & Orphan Integrity",
            "status": status,
            "market_orphans": market_orphans,
            "technical_orphans": tech_orphans,
            "financial_orphans": fin_orphans,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # 9. Point-in-Time Historical Safety (Backtest Contract Check)
    # ------------------------------------------------------------
    def check_point_in_time_safety(self) -> Dict[str, Any]:
        violations = []
        tested_count = 0

        for symbol in self.REPRESENTATIVE_SYMBOLS:
            records = get_backtest_inputs(symbol, "2025-08-01", "2025-08-28")
            tested_count += len(records)

            for rec in records:
                eval_date = str(rec.get("evaluation_date"))[:10]
                reporting_period = rec.get("reporting_period")
                if reporting_period is not None:
                    reporting_period = str(reporting_period)[:10]
                    if reporting_period > eval_date:
                        violations.append({
                            "symbol": symbol,
                            "evaluation_date": eval_date,
                            "reporting_period": reporting_period,
                        })

        status = "PASS"
        if violations:
            status = "BLOCKING FAILURE"
            self.blocking_failures.append(
                f"Point-in-time future financial leakage detected: {len(violations)} violations"
            )

        return {
            "check": "Point-in-Time Historical Safety",
            "status": status,
            "symbols_tested": self.REPRESENTATIVE_SYMBOLS,
            "records_evaluated": tested_count,
            "violations_count": len(violations),
            "violations": violations,
            "passed": status == "PASS",
        }

    # ------------------------------------------------------------
    # Run Full Quality Monitoring Audit
    # ------------------------------------------------------------
    def run_all_checks(self) -> Dict[str, Any]:
        print("=" * 70)
        print("WEEK 15 - DATA QUALITY MONITORING AUDIT")
        print("=" * 70)

        conn = self.get_connection()
        try:
            self.results["universe_integrity"] = self.check_universe_integrity(conn)
            self.results["market_coverage"] = self.check_market_data_coverage(conn)
            self.results["technical_sync"] = self.check_technical_synchronization(conn)
            self.results["financial_coverage"] = self.check_financial_data(conn)
            self.results["classification"] = self.check_classification_mappings(conn)
            self.results["duplicates"] = self.check_duplicate_records(conn)
            self.results["market_anomalies"] = self.check_market_anomalies(conn)
            self.results["orphans"] = self.check_orphan_records(conn)
        finally:
            conn.close()

        # Service contract point-in-time check
        self.results["point_in_time_safety"] = self.check_point_in_time_safety()

        # Overall Status
        if self.blocking_failures:
            overall_status = "BLOCKING FAILURE"
        elif self.warnings:
            overall_status = "PASS WITH WARNINGS"
        else:
            overall_status = "PASS"

        # Print formatted CLI summary
        for key, res in self.results.items():
            chk_name = res["check"]
            st = res["status"]
            icon = "[PASS]" if st == "PASS" else ("[WARN]" if st == "WARNING" else "[FAIL]")
            print(f"{icon:<7} {chk_name:<48} {st}")

        print("-" * 70)
        print(f"OVERALL QUALITY STATUS: {overall_status}")
        print(f"Blocking Failures : {len(self.blocking_failures)}")
        print(f"Warnings          : {len(self.warnings)}")

        if self.warnings:
            print("\nOperational Warnings:")
            for w in self.warnings:
                print(f"  - {w}")

        if self.blocking_failures:
            print("\nBlocking Failures:")
            for f in self.blocking_failures:
                print(f"  - {f}")

        report_payload = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "blocking_failures_count": len(self.blocking_failures),
            "warnings_count": len(self.warnings),
            "blocking_failures": self.blocking_failures,
            "warnings": self.warnings,
            "details": self.results,
        }

        report_path = REPORTS_DIR / "week15_quality_monitoring_report.json"
        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report_payload, file, indent=2)

        print("\n" + "=" * 70)
        print(f"Quality audit report saved to {report_path}")
        print("=" * 70)

        return report_payload


def main():
    monitor = Week15QualityMonitor()
    report = monitor.run_all_checks()
    if report["overall_status"] == "BLOCKING FAILURE":
        sys.exit(1)


if __name__ == "__main__":
    main()
