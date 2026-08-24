"""
Week 9 - Persistent Failure Reporting

Purpose:
    Persist failed stock processing information so failures
    are available after the daily pipeline finishes.

This module does NOT:
    - retry stocks
    - generate BUY/SELL signals
    - make trading decisions
"""

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOG_DIRECTORY = PROJECT_ROOT / "logs"
FAILURE_FILE = LOG_DIRECTORY / "failed_stocks.json"


def load_failures():
    """
    Load previously recorded failures.

    Returns:
        list: Failure records.
    """

    if not FAILURE_FILE.exists():
        return []

    try:
        with FAILURE_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):

        return []


def save_failures(failures):
    """
    Persist failure records to disk.
    """

    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = FAILURE_FILE.with_suffix(
        ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            failures,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_file.replace(
        FAILURE_FILE
    )


def record_failure(
    symbol,
    stage,
    reason,
):
    """
    Record a failed stock operation.

    Existing identical unresolved failures are not duplicated.
    """

    failures = load_failures()

    symbol = str(symbol).upper().strip()
    stage = str(stage).strip()
    reason = str(reason).strip()

    for failure in failures:

        if (
            failure.get("symbol") == symbol
            and failure.get("stage") == stage
            and failure.get("reason") == reason
            and failure.get("status") == "FAILED"
        ):

            return False

    failures.append(
        {
            "symbol": symbol,
            "stage": stage,
            "reason": reason,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "FAILED",
        }
    )

    save_failures(failures)

    return True


def get_failed_stocks():
    """
    Return unresolved failed-stock records.
    """

    return [
        failure
        for failure in load_failures()
        if failure.get("status") == "FAILED"
    ]


def mark_resolved(
    symbol,
    stage=None,
):
    """
    Mark matching failure records as resolved.
    """

    failures = load_failures()

    symbol = str(symbol).upper().strip()

    changed = False

    for failure in failures:

        if failure.get("symbol") != symbol:
            continue

        if (
            stage is not None
            and failure.get("stage") != stage
        ):
            continue

        if failure.get("status") != "FAILED":
            continue

        failure["status"] = "RESOLVED"
        failure["resolved_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        changed = True

    if changed:
        save_failures(failures)

    return changed


def clear_resolved():
    """
    Remove resolved records from the failure file.
    """

    failures = load_failures()

    active = [
        failure
        for failure in failures
        if failure.get("status") == "FAILED"
    ]

    save_failures(active)

    return len(failures) - len(active)


if __name__ == "__main__":

    print("=" * 60)
    print("WEEK 9 - FAILURE REPORTING")
    print("=" * 60)

    failures = get_failed_stocks()

    print(
        f"Unresolved failures: {len(failures)}"
    )

    for failure in failures:

        print(
            f"{failure['symbol']} | "
            f"{failure['stage']} | "
            f"{failure['reason']}"
        )