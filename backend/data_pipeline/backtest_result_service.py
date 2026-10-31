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
from datetime import datetime, timezone
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
    Create the backtest_results, backtest_runs, backtest_trades, and
    backtest_equity_curve tables along with their indexes if they do not already exist.
    """

    connection = get_connection()

    try:
        # 1. Legacy / Summary table backtest_results
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

        # 2. Portfolio-level run tracking
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_runs (
                run_id TEXT PRIMARY KEY,
                strategy_version TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                config_json TEXT NOT NULL,
                status TEXT NOT NULL,
                metrics_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
            """
        )

        # 3. Normalized trade executions
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'LONG',
                signal_date TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_date TEXT,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                initial_value REAL NOT NULL,
                gross_pl REAL,
                entry_costs REAL NOT NULL DEFAULT 0.0,
                exit_costs REAL NOT NULL DEFAULT 0.0,
                total_costs REAL NOT NULL DEFAULT 0.0,
                net_pl REAL,
                return_pct REAL,
                status TEXT NOT NULL,
                exit_reason TEXT,
                holding_days INTEGER DEFAULT 0,
                trade_metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_backtest_trades_run_symbol
            ON backtest_trades(run_id, symbol)
            """
        )

        # 4. Daily Portfolio Equity Curve
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_equity_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                date TEXT NOT NULL,
                cash REAL NOT NULL,
                positions_value REAL NOT NULL,
                total_equity REAL NOT NULL,
                drawdown_pct REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(run_id, date)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_backtest_equity_curve_run_date
            ON backtest_equity_curve(run_id, date)
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


def validate_backtest_result(result: Dict[str, Any]) -> bool:
    """
    Validate that a backtest result contains all required fields.

    Required fields:
    - run_id
    - symbol
    - evaluation_date
    - result_metadata

    Returns True when the result is valid.
    Raises ValueError when required data is missing or invalid.
    """

    if not isinstance(result, dict):
        raise ValueError(
            "Backtest result must be a dictionary."
        )

    required_fields = (
        "run_id",
        "symbol",
        "evaluation_date",
        "result_metadata",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing_fields:
        raise ValueError(
            "Missing required backtest result fields: "
            + ", ".join(missing_fields)
        )

    _validate_run_id(result["run_id"])
    _validate_symbol(result["symbol"])
    _validate_date(result["evaluation_date"])

    if not isinstance(
        result["result_metadata"],
        dict,
    ):
        raise ValueError(
            "result_metadata must be a dictionary."
        )

    return True


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

            validate_backtest_result(result)

            run_id = _validate_run_id(
                result["run_id"]
            )

            symbol = _validate_symbol(
                result["symbol"]
            )

            evaluation_date = _validate_date(
                result["evaluation_date"]
            )

            metadata = result["result_metadata"]

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


def store_portfolio_backtest_run(
    run_id: str,
    strategy_version: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    trades: List[Dict[str, Any]],
    equity_curve: List[Dict[str, Any]],
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Stores an entire sequential portfolio backtest run transactionally across
    backtest_runs, backtest_trades, backtest_equity_curve, and backtest_results.

    Parameters
    ----------
    run_id : str
        Unique backtest run identifier.
    strategy_version : str
        Strategy tag (e.g. "V1_SWING").
    start_date : str
        Simulation start date (YYYY-MM-DD).
    end_date : str
        Simulation end date (YYYY-MM-DD).
    initial_capital : float
        Starting cash balance.
    config : dict
        Simulation parameters (sizing, capital, costs).
    metrics : dict
        Calculated performance summary.
    trades : list of dict
        Individual simulated trade records.
    equity_curve : list of dict
        Chronological portfolio equity milestones.
    overwrite : bool, default False
        If True, replaces an existing run with the same run_id.
        If False, raises ValueError on duplicate run_id.

    Returns
    -------
    dict
        Summary of stored items: {'run_id': run_id, 'trades_count': int, 'equity_points': int}.
    """
    initialize_backtest_results_table()

    run_id = _validate_run_id(run_id)
    start_date = _validate_date(start_date)
    end_date = _validate_date(end_date)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check existing run
        cursor.execute("SELECT run_id FROM backtest_runs WHERE run_id = ?", (run_id,))
        existing_run = cursor.fetchone()

        if existing_run:
            if not overwrite:
                raise ValueError(f"Backtest run '{run_id}' already exists. Use overwrite=True to replace.")
            # Delete previous run records atomically
            cursor.execute("DELETE FROM backtest_runs WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM backtest_trades WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM backtest_equity_curve WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM backtest_results WHERE run_id = ?", (run_id,))

        completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # 1. Insert into backtest_runs
        cursor.execute(
            """
            INSERT INTO backtest_runs (
                run_id, strategy_version, start_date, end_date, initial_capital,
                config_json, status, metrics_json, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                strategy_version,
                start_date,
                end_date,
                float(initial_capital),
                json.dumps(config, default=str, sort_keys=True),
                "COMPLETED",
                json.dumps(metrics, default=str, sort_keys=True),
                completed_at
            )
        )

        # 2. Insert into backtest_trades
        trades_count = 0
        for t in trades:
            raw_uid = t.get("trade_id")
            if raw_uid:
                trade_uid = raw_uid if raw_uid.startswith(f"{run_id}_") else f"{run_id}_{raw_uid}"
            else:
                trade_uid = f"{run_id}_{t['symbol']}_{t.get('entry_date') or t['evaluation_date']}_{trades_count+1}"
            cursor.execute(
                """
                INSERT INTO backtest_trades (
                    trade_id, run_id, symbol, direction, signal_date, entry_date,
                    entry_price, exit_date, exit_price, quantity, initial_value,
                    gross_pl, entry_costs, exit_costs, total_costs, net_pl,
                    return_pct, status, exit_reason, holding_days, trade_metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_uid,
                    run_id,
                    t["symbol"],
                    t.get("direction", "LONG"),
                    t.get("evaluation_date", ""),
                    t.get("entry_date", ""),
                    float(t.get("entry_price") or 0.0),
                    t.get("exit_date"),
                    float(t.get("exit_price")) if t.get("exit_price") is not None else None,
                    int(t.get("quantity") or 1),
                    float(t.get("initial_value") or 0.0),
                    float(t.get("gross_pl")) if t.get("gross_pl") is not None else None,
                    float(t.get("entry_costs") or 0.0),
                    float(t.get("exit_costs") or 0.0),
                    float(t.get("total_costs") or 0.0),
                    float(t.get("net_pl")) if t.get("net_pl") is not None else (float(t.get("pl")) if t.get("pl") is not None else None),
                    float(t.get("return_pct")) if t.get("return_pct") is not None else None,
                    t.get("status", "CLOSED"),
                    t.get("exit_reason"),
                    int(t.get("holding_days") or 0),
                    json.dumps(t.get("trade_quality") or {}, default=str)
                )
            )
            trades_count += 1

            # Also write into backtest_results for backward-compatible queries
            cursor.execute(
                """
                INSERT OR REPLACE INTO backtest_results (
                    run_id, symbol, evaluation_date, result_metadata
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    run_id,
                    t["symbol"],
                    t.get("evaluation_date", ""),
                    json.dumps({
                        "trade_id": trade_uid,
                        "status": t.get("status"),
                        "recommendation": t.get("recommendation"),
                        "signal_valid": t.get("signal_valid", True),
                        "is_eligible": t.get("is_eligible", True),
                        "entry_date": t.get("entry_date"),
                        "entry_price": t.get("entry_price"),
                        "exit_date": t.get("exit_date"),
                        "exit_price": t.get("exit_price"),
                        "exit_reason": t.get("exit_reason"),
                        "quantity": t.get("quantity", 1),
                        "initial_value": t.get("initial_value"),
                        "gross_pl": t.get("gross_pl"),
                        "entry_costs": t.get("entry_costs", 0.0),
                        "exit_costs": t.get("exit_costs", 0.0),
                        "total_costs": t.get("total_costs", 0.0),
                        "net_pl": t.get("net_pl"),
                        "pl": t.get("net_pl") if t.get("net_pl") is not None else t.get("pl"),
                        "return_pct": t.get("return_pct"),
                        "holding_days": t.get("holding_days", 0),
                    }, default=str, sort_keys=True)
                )
            )

        # 3. Insert into backtest_equity_curve
        equity_points = 0
        for pt in equity_curve:
            d_str = pt.get("date")
            if not d_str:
                continue
            cursor.execute(
                """
                INSERT OR REPLACE INTO backtest_equity_curve (
                    run_id, date, cash, positions_value, total_equity, drawdown_pct
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    d_str,
                    float(pt.get("cash") or 0.0),
                    float(pt.get("positions_value") or 0.0),
                    float(pt.get("equity") or 0.0),
                    float(pt.get("drawdown_pct") or 0.0)
                )
            )
            equity_points += 1

        connection.commit()
        return {
            "run_id": run_id,
            "trades_count": trades_count,
            "equity_points": equity_points,
            "status": "COMPLETED"
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_backtest_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details and metrics of a specific backtest run."""
    initialize_backtest_results_table()
    run_id = _validate_run_id(run_id)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT run_id, strategy_version, start_date, end_date, initial_capital,
                   config_json, status, metrics_json, created_at, completed_at
            FROM backtest_runs
            WHERE run_id = ?
            """,
            (run_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "run_id": row[0],
            "strategy_version": row[1],
            "start_date": row[2],
            "end_date": row[3],
            "initial_capital": row[4],
            "config": json.loads(row[5]) if row[5] else {},
            "status": row[6],
            "metrics": json.loads(row[7]) if row[7] else {},
            "created_at": row[8],
            "completed_at": row[9]
        }
    finally:
        connection.close()


def get_latest_backtest_run() -> Optional[Dict[str, Any]]:
    """Retrieve the most recent backtest run."""
    initialize_backtest_results_table()
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT run_id
            FROM backtest_runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        return get_backtest_run(row[0])
    finally:
        connection.close()


def get_backtest_trades(
    run_id: str,
    symbol: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve trade execution records for a backtest run."""
    initialize_backtest_results_table()
    run_id = _validate_run_id(run_id)

    query = """
        SELECT trade_id, run_id, symbol, direction, signal_date, entry_date,
               entry_price, exit_date, exit_price, quantity, initial_value,
               gross_pl, entry_costs, exit_costs, total_costs, net_pl,
               return_pct, status, exit_reason, holding_days, trade_metadata, created_at
        FROM backtest_trades
        WHERE run_id = ?
    """
    params = [run_id]

    if symbol:
        query += " AND symbol = ?"
        params.append(_validate_symbol(symbol))

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY entry_date ASC, id ASC"

    connection = get_connection()
    try:
        cursor = connection.cursor()
        rows = cursor.execute(query, params).fetchall()
        trades = []
        for r in rows:
            trades.append({
                "trade_id": r[0],
                "run_id": r[1],
                "symbol": r[2],
                "direction": r[3],
                "evaluation_date": r[4],
                "entry_date": r[5],
                "entry_price": r[6],
                "exit_date": r[7],
                "exit_price": r[8],
                "quantity": r[9],
                "initial_value": r[10],
                "gross_pl": r[11],
                "entry_costs": r[12],
                "exit_costs": r[13],
                "total_costs": r[14],
                "net_pl": r[15],
                "pl": r[15] if r[15] is not None else r[11],
                "return_pct": r[16],
                "status": r[17],
                "exit_reason": r[18],
                "holding_days": r[19],
                "trade_quality": json.loads(r[20]) if r[20] else {},
                "created_at": r[21]
            })
        return trades
    finally:
        connection.close()


def get_backtest_equity_curve(run_id: str) -> List[Dict[str, Any]]:
    """Retrieve chronological equity curve data for a backtest run."""
    initialize_backtest_results_table()
    run_id = _validate_run_id(run_id)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT date, cash, positions_value, total_equity, drawdown_pct
            FROM backtest_equity_curve
            WHERE run_id = ?
            ORDER BY date ASC
            """,
            (run_id,)
        ).fetchall()

        curve = []
        for r in rows:
            curve.append({
                "date": r[0],
                "cash": r[1],
                "positions_value": r[2],
                "equity": r[3],
                "drawdown_pct": r[4]
            })
        return curve
    finally:
        connection.close()


def delete_backtest_run(run_id: str) -> bool:
    """Atomically delete all records associated with a backtest run."""
    initialize_backtest_results_table()
    run_id = _validate_run_id(run_id)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM backtest_runs WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM backtest_trades WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM backtest_equity_curve WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM backtest_results WHERE run_id = ?", (run_id,))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()