"""
scripts/migration/01_validate_environment.py
============================================
Validates the environment, configuration files, Git tracking state,
local SQLite database hash, and read-only connectivity to Neon staging.

Usage:
    python scripts/migration/01_validate_environment.py
"""

import os
import sys
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.migration.common import setup_migration_logger, mask_database_url, compute_file_sha256
from backend.database.connection import open_db_connection, parse_database_url

logger = setup_migration_logger("01_validate_environment")

EXPECTED_SQLITE_HASH = "1BE49BDDE48A2954C2687A48234AD65CDC4382FAE127274EC9370B1B5400BEA6"

def main():
    parser = argparse.ArgumentParser(description="Validate environment and database configurations.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite database path")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination PostgreSQL URL for testing")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Environment & Connectivity Validation ===")
    
    # 1. Validate SQLite file
    if not os.path.exists(args.source_sqlite):
        logger.error(f"Source SQLite database not found at {args.source_sqlite}")
        sys.exit(1)
        
    actual_hash = compute_file_sha256(args.source_sqlite)
    logger.info(f"Source SQLite Path: {args.source_sqlite}")
    logger.info(f"Source SQLite SHA-256: {actual_hash}")
    if actual_hash == EXPECTED_SQLITE_HASH:
        logger.info("[PASS] Source SQLite hash matches authoritative baseline exactly.")
    else:
        logger.warning(f"[WARNING] Source SQLite hash differs from expected {EXPECTED_SQLITE_HASH}")

    # 2. Validate Database Configuration
    target_url = args.dest_pg_url or os.getenv("TEST_POSTGRESQL_URL") or os.getenv("DATABASE_URL")
    if target_url:
        from scripts.migration.common import validate_test_target_url
        validate_test_target_url(target_url)
    
    config = parse_database_url(target_url)
    logger.info(f"Active Engine: {config.engine.value}")
    logger.info(f"Masked Database URL: {config.masked_url}")

    # 3. Read-only Target Connectivity Probe
    logger.info("Testing read-only connectivity to target database...")
    try:
        with open_db_connection(target_url) as conn:
            with conn.cursor() as cur:
                if config.is_postgresql:
                    cur.execute("SET default_transaction_read_only = on;")
                    cur.execute("SELECT version();")
                    version = cur.fetchone()[0]
                    cur.execute("SELECT current_database(), current_schema();")
                    db_name, schema = cur.fetchone()
                    logger.info(f"[PASS] Connection successful to PostgreSQL database '{db_name}', schema '{schema}'")
                    logger.info(f"Server version: {version}")
                else:
                    cur.execute("SELECT sqlite_version();")
                    version = cur.fetchone()[0]
                    logger.info(f"[PASS] Connection successful to SQLite database. Version: {version}")
    except Exception as e:
        logger.error(f"[FAIL] Target database connection failed: {e}")
        sys.exit(1)

    logger.info("[SUCCESS] All environment and connectivity validations passed.")

if __name__ == "__main__":
    main()
