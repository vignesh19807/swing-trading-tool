"""
Week 14 - Backtest Result Service

Provides persistence and retrieval for historical backtest results.

Data Engineer boundary:
- Stores downstream backtest outputs.
- Retrieves stored results.
- Does not calculate trading signals.
- Does not make trading decisions.
- Does not modify the Logic Engine.
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


def get_connection():
    """Create a connection to the project SQLite database."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    return sqlite3.connect(DATABASE_PATH)


def initialize_backtest_results_table():
    """
    Create the backtest_results table and its composite index
    if they do not already exist.
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                evaluation_date TEXT NOT NULL,
                result_metadata TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(run_id, symbol, evaluation_date)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_backtest_results_run_symbol_date
            ON backtest_results(
                run_id,
                symbol,
                evaluation_date
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def _validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol."""

    if not isinstance(symbol, str):
        raise ValueError(
            "Symbol must be a non-empty string."
        )

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError(
            "Symbol must be a non-empty string."
        )

    return symbol


def _validate_date(date_str: str) -> str:
    """Validate YYYY-MM-DD date format."""

    if not isinstance(date_str, str):
        raise ValueError(
            "Date must be a string in YYYY-MM-DD format."
        )

    date_str = date_str.strip()

    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        date_str,
    ):
        raise ValueError(
            f"Invalid date '{date_str}'. "
            "Expected YYYY-MM-DD."
        )

    try:
        datetime.strptime(
            date_str,
            "%Y-%m-%d",
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid calendar date '{date_str}'."
        ) from exc

    return date_str


def _validate_run_id(run_id: str) -> str:
    """Validate the backtest run identifier."""

    if not isinstance(run_id, str):
        raise ValueError(
            "run_id must be a non-empty string."
        )

    run_id = run_id.strip()

    if not run_id:
        raise ValueError(
            "run_id must be a non-empty string."
        )

    return run_id


def store_backtest_result(
    run_id: str,
    symbol: str,
    evaluation_date: str,
    result_metadata: Dict[str, Any],
) -> bool:
    """
    Store one backtest result.

    Returns True when the result is successfully stored.

    Duplicate run_id + symbol + evaluation_date combinations
    are rejected by the database constraint.
    """

    initialize_backtest_results_table()

    run_id = _validate_run_id(run_id)
    symbol = _validate_symbol(symbol)
    evaluation_date = _validate_date(evaluation_date)

    if not isinstance(result_metadata, dict):
        raise ValueError(
            "result_metadata must be a dictionary."
        )

    metadata_json = json.dumps(
        result_metadata,
        default=str,
        sort_keys=True,
    )

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO backtest_results (
                run_id,
                symbol,
                evaluation_date,
                result_metadata
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                symbol,
                evaluation_date,
                metadata_json,
            ),
        )

        connection.commit()
        return True

    except sqlite3.IntegrityError:
        connection.rollback()
        return False

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_backtest_results(
    run_id: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve stored backtest results using optional filters.
    """

    initialize_backtest_results_table()

    conditions = []
    parameters = []

    if run_id is not None:
        run_id = _validate_run_id(run_id)
        conditions.append("run_id = ?")
        parameters.append(run_id)

    if symbol is not None:
        symbol = _validate_symbol(symbol)
        conditions.append("symbol = ?")
        parameters.append(symbol)

    if start_date is not None:
        start_date = _validate_date(start_date)
        conditions.append("evaluation_date >= ?")
        parameters.append(start_date)

    if end_date is not None:
        end_date = _validate_date(end_date)
        conditions.append("evaluation_date <= ?")
        parameters.append(end_date)

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise ValueError(
            "start_date must be earlier than or equal to end_date."
        )

    query = """
        SELECT
            id,
            run_id,
            symbol,
            evaluation_date,
            result_metadata,
            created_at
        FROM backtest_results
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY evaluation_date ASC, symbol ASC
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        results = []

        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "run_id": row[1],
                    "symbol": row[2],
                    "evaluation_date": row[3],
                    "result_metadata": json.loads(row[4]),
                    "created_at": row[5],
                }
            )

        return results

    finally:
        connection.close()


def store_backtest_results(
    results: List[Dict[str, Any]],
) -> int:
    """
    Store multiple backtest results in one transaction.

    Returns the number of successfully inserted records.
    """

    if not isinstance(results, list):
        raise ValueError(
            "results must be a list."
        )

    initialize_backtest_results_table()

    connection = get_connection()

    try:
        inserted = 0

        for result in results:

            run_id = _validate_run_id(
                result.get("run_id")
            )

            symbol = _validate_symbol(
                result.get("symbol")
            )

            evaluation_date = _validate_date(
                result.get("evaluation_date")
            )

            metadata = result.get(
                "result_metadata"
            )

            if not isinstance(metadata, dict):
                raise ValueError(
                    "result_metadata must be a dictionary."
                )

            connection.execute(
                """
                INSERT INTO backtest_results (
                    run_id,
                    symbol,
                    evaluation_date,
                    result_metadata
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    run_id,
                    symbol,
                    evaluation_date,
                    json.dumps(
                        metadata,
                        default=str,
                        sort_keys=True,
                    ),
                ),
            )

            inserted += 1

        connection.commit()
        return inserted

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()