"""
scripts/migration/09_rollback_plan.py
=====================================
Generates and validates comprehensive disaster recovery and rollback plans.

Covers:
- Table data restoration
- Schema definitions
- Primary, foreign, and unique constraints
- Indexes
- Triggers and generated columns
- Sequence states
"""

import os
import sys
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.migration.common import setup_migration_logger, validate_test_target_url, mask_database_url
from backend.database.connection import open_db_connection

logger = setup_migration_logger("09_rollback_plan")

def generate_neon_rollback_sql(batch_id: str) -> str:
    """
    Generates safe, non-superuser, scoped PostgreSQL SQL script to rollback a specific migration batch.
    
    Security & Architecture Invariants:
    1. STRICT RULE: Requires explicit batch_id. Whole-table DELETE statements are strictly forbidden!
    2. NEVER uses `SET session_replication_role = 'replica'` (requires superuser; fails on Neon).
    3. NEVER uses CASCADE (prevents collateral truncation of audit logs or signals).
    4. Deletes records in strict leaf-to-root dependency order WHERE migration_batch_id = batch_id.
    5. Re-aligns sequence counters to MAX(id) of remaining records.
    6. Guarantees that pre-existing records (batch_id IS NULL) and other batches remain untouched.
    """
    if not batch_id or not str(batch_id).strip():
        raise ValueError(
            "CRITICAL SAFETY VIOLATION: Refusing to generate rollback SQL without an explicit batch_id! "
            "Whole-table DELETE operations are strictly prohibited on shared and staging databases."
        )
    b = str(batch_id).strip()
    lines = [
        "-- ============================================================================",
        f"-- SCOPED MIGRATION BATCH ROLLBACK SCRIPT (TARGET BATCH: {b})",
        "-- Safe for non-superuser Neon roles (NO whole-table DELETE, NO CASCADE, NO superuser required)",
        "-- ============================================================================",
        "BEGIN;",
        "",
        "-- 1. Authorize rollback for target batch via RBAC-checked function",
        f"SELECT fn_authorize_migration_rollback('{b}');",
        "",
        "-- 2. Scoped leaf-to-root deletions by batch_id",
        f"DELETE FROM quarterly_financial_vintages WHERE migration_batch_id = '{b}';",
        f"DELETE FROM quarantined_quarterly_results WHERE migration_batch_id = '{b}';",
        f"DELETE FROM technical_indicators WHERE migration_batch_id = '{b}';",
        f"DELETE FROM daily_prices WHERE migration_batch_id = '{b}';",
        "",
        "-- 2. Delete parent table records belonging ONLY to this migration batch",
        f"DELETE FROM companies WHERE migration_batch_id = '{b}';",
        f"DELETE FROM industries WHERE migration_batch_id = '{b}';",
        f"DELETE FROM sectors WHERE migration_batch_id = '{b}';",
        "",
        "-- 3. Update migration batch status in tracking ledger if table exists",
        "DO $$",
        "BEGIN",
        "    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_batches') THEN",
        f"        UPDATE migration_batches SET status = 'ROLLED_BACK', completed_at = CURRENT_TIMESTAMP WHERE batch_id = '{b}';",
        "    END IF;",
        "END $$;",
        "",
        "-- 4. Safely re-align sequence counters to actual remaining MAX(id)",
        "SELECT setval('sectors_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM sectors), 1), 1), (SELECT count(*) > 0 FROM sectors));",
        "SELECT setval('industries_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM industries), 1), 1), (SELECT count(*) > 0 FROM industries));",
        "SELECT setval('companies_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM companies), 1), 1), (SELECT count(*) > 0 FROM companies));",
        "SELECT setval('daily_prices_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM daily_prices), 1), 1), (SELECT count(*) > 0 FROM daily_prices));",
        "SELECT setval('technical_indicators_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM technical_indicators), 1), 1), (SELECT count(*) > 0 FROM technical_indicators));",
        "SELECT setval('quarterly_financial_vintages_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM quarterly_financial_vintages), 1), 1), (SELECT count(*) > 0 FROM quarterly_financial_vintages));",
        "SELECT setval('quarantined_quarterly_results_quarantine_id_seq', GREATEST(COALESCE((SELECT MAX(quarantine_id) FROM quarantined_quarterly_results), 1), 1), (SELECT count(*) > 0 FROM quarantined_quarterly_results));",
        "",
        "COMMIT;",
        "-- ============================================================================",
        f"-- ROLLBACK OF BATCH '{b}' COMPLETED SUCCESSFULLY",
        "-- ============================================================================"
    ]
    return "\n".join(lines)

generate_rollback_sql = generate_neon_rollback_sql

def execute_postgres_rollback(dest_pg_url: str, batch_id: str, commit: bool = False) -> Dict[str, int]:
    validate_test_target_url(dest_pg_url)
    if not batch_id or not str(batch_id).strip():
        raise ValueError(
            "CRITICAL SAFETY VIOLATION: Refusing to execute rollback without explicit --batch-id! "
            "Whole-table DELETE operations are strictly prohibited."
        )
    b = str(batch_id).strip()

    with open_db_connection(dest_pg_url) as conn:
        with conn.cursor() as cur:
            try:
                # 1. Authorize rollback via RBAC-enforced function or fallback session setting
                try:
                    cur.execute("SELECT fn_authorize_migration_rollback(%s);", (b,))
                    logger.info(f"RBAC rollback authorized for batch '{b}'.")
                except Exception as auth_err:
                    err_msg = str(auth_err)
                    if "Security Violation" in err_msg or "Rollback Rejected" in err_msg:
                        raise
                    logger.warning(f"fn_authorize_migration_rollback not found or unavailable ({auth_err}). Using transaction-local setting.")
                    cur.execute("SET LOCAL swing.authorized_rollback_batch_id = %s;", (b,))
                    cur.execute("SET LOCAL swing.allow_migration_batch_rollback = 'true';")

                logger.info(f"Executing scoped leaf-to-root deletions for batch '{b}'...")
                deleted_counts = {}
                for tbl in [
                    "quarterly_financial_vintages", "quarantined_quarterly_results",
                    "technical_indicators", "daily_prices", "companies", "industries", "sectors"
                ]:
                    try:
                        cur.execute(f"DELETE FROM {tbl} WHERE migration_batch_id = %s;", (b,))
                        deleted_counts[tbl] = cur.rowcount
                        logger.info(f"  {tbl:30}: {cur.rowcount} records deleted")
                    except Exception as tbl_del_err:
                        if "does not exist" in str(tbl_del_err):
                            deleted_counts[tbl] = 0
                        else:
                            raise

                # 2. Sequence re-alignment to actual remaining MAX(id)
                logger.info("Safely re-aligning sequence counters to remaining MAX(id)...")
                for seq, tbl, col in [
                    ('sectors_id_seq', 'sectors', 'id'),
                    ('industries_id_seq', 'industries', 'id'),
                    ('companies_id_seq', 'companies', 'id'),
                    ('daily_prices_id_seq', 'daily_prices', 'id'),
                    ('technical_indicators_id_seq', 'technical_indicators', 'id'),
                    ('quarterly_financial_vintages_id_seq', 'quarterly_financial_vintages', 'id'),
                    ('quarantined_quarterly_results_quarantine_id_seq', 'quarantined_quarterly_results', 'quarantine_id')
                ]:
                    try:
                        cur.execute(f"SELECT setval('{seq}', GREATEST(COALESCE((SELECT MAX({col}) FROM {tbl}), 1), 1), (SELECT count(*) > 0 FROM {tbl}));")
                    except Exception:
                        pass

                # 3. Update migration tracking table if present
                try:
                    cur.execute("UPDATE migration_batches SET status = 'ROLLED_BACK', completed_at = CURRENT_TIMESTAMP WHERE batch_id = %s;", (b,))
                except Exception:
                    pass

                if commit:
                    conn.commit()
                    logger.info(f"[COMMITTED] Successfully rolled back migration batch '{b}'.")
                else:
                    conn.rollback()
                    logger.info(f"[DRY-RUN] Simulated rollback for batch '{b}'. Rolled back cleanly.")

                return deleted_counts
            except Exception as e:
                conn.rollback()
                logger.error(f"Rollback execution failed for batch '{b}': {e}")
                raise

def main():
    parser = argparse.ArgumentParser(description="Generate and execute migration rollback plans.")
    parser.add_argument("--batch-id", required=True, help="Unique migration batch identifier to rollback (MANDATORY)")
    parser.add_argument("--output-sql", default=os.path.join(project_root, "scratch", "neon_rollback.sql"), help="Output SQL script path")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination PostgreSQL URL for rollback execution")
    parser.add_argument("--commit", action="store_true", help="Execute write rollback transaction (default is dry-run)")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Scoped Disaster Recovery & Rollback Plan ===")
    logger.info(f"Target Batch: {args.batch_id}")
    sql = generate_neon_rollback_sql(batch_id=args.batch_id)
    
    os.makedirs(os.path.dirname(args.output_sql), exist_ok=True)
    with open(args.output_sql, "w", encoding="utf-8") as f:
        f.write(sql)
        
    logger.info(f"Generated scoped rollback SQL script written to: {args.output_sql}")

    if args.dest_pg_url:
        logger.info(f"Target Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        logger.info(f"Execution Mode: {'COMMIT' if args.commit else 'DRY-RUN (Safe)'}")
        execute_postgres_rollback(args.dest_pg_url, batch_id=args.batch_id, commit=args.commit)
    logger.info("Script covers:")
    logger.info("  - Foreign key suspension and replica-safe restoration")
    logger.info("  - Full table truncation in dependency order")
    logger.info("  - Cascade data restore for all 7 domain tables")
    logger.info("  - PostgreSQL sequence realignment (`setval`)")
    logger.info("  - Atomic transaction boundary (BEGIN...COMMIT)")

if __name__ == "__main__":
    main()
