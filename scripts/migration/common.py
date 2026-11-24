"""
scripts/migration/common.py
===========================
Shared utilities, canonical checksum formulas, conflict resolution engine,
and safety boundaries for Phase 7.2C migration tooling.

Strict Invariants:
1. Dry-run mode by default.
2. Credentials masked in all outputs and representations.
3. No automatic overwrite of conflicting destination records.
4. Point-in-time financial provenance strictly preserved (zero promotion, zero inference).
"""

from __future__ import annotations

import os
import sys
import json
import logging
import sqlite3
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

# Configure logging
def setup_migration_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_migration_logger("migration.common")


def mask_database_url(url: str) -> str:
    """Masks user credentials in connection strings."""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        if not parts.scheme:
            return url
        if parts.password is not None or parts.username is not None:
            user = parts.username or ""
            host = parts.hostname or ""
            port = f":{parts.port}" if parts.port else ""
            masked_netloc = f"{user}:***@{host}{port}"
            return urlunsplit((parts.scheme, masked_netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:
        return "<malformed_url>"


def compute_file_sha256(file_path: str) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def validate_test_target_url(target: Optional[str]) -> None:
    """
    Enforces strict database isolation: rejects real Neon cloud staging/production databases
    during testing and migration validation phases.
    """
    if not target:
        return
    lower_target = str(target).lower()
    if "neon.tech" in lower_target or "aws.neon.tech" in lower_target:
        raise ValueError(
            "CRITICAL SAFETY VIOLATION: Execution against real Neon database is strictly prohibited in Phase 7.2C.2! "
            f"Target URL: {mask_database_url(target)}"
        )


def is_postgres_url(target: Optional[str]) -> bool:
    """Returns True if the target string specifies a PostgreSQL URL."""
    if not target:
        return False
    return str(target).strip().startswith(("postgresql://", "postgres://"))



# ==============================================================================
# CANONICAL DETERMINISTIC SHA-256 CHECKSUM DESIGN & NUMERIC PRECISION POLICY
# ==============================================================================
# Architectural Decoupling (Phase 7.2C.7):
# 1. Reconciliation & Drift Tolerance Policy:
#    - FINANCIAL_TOLERANCE = 1e-4 (0.0001 Cr = Rs. 1,000 resolution).
#    - MARKET_PRICE_TOLERANCE = 1e-4 (0.0001 INR).
#    Applied exclusively in conflict resolution engines to classify matching vs conflicting rows.
# 2. Exact Migration Integrity Hashing Policy:
#    - Bit-exact canonical hashing without silent 4-decimal truncation.
#    - Formats numbers preserving full precision up to 10 decimals without trailing zero noise.
#    - Eliminates IEEE 754 platform artifacts while preserving all significant figures.
# ==============================================================================

FINANCIAL_TOLERANCE: float = 1e-4
MARKET_PRICE_TOLERANCE: float = 1e-4


def _norm_float(val: Any, exact: bool = False) -> str:
    """
    Normalizes a float value.
    If exact=True: Preserves full precision without lossy 4-decimal rounding (up to 10 decimal places, trimmed).
    If exact=False: Formats to standard 4 decimal places (0.0001 resolution).
    """
    if val is None or str(val).strip().upper() == "NULL" or str(val).strip() == "":
        return "NULL"
    try:
        f_val = float(val)
        if exact:
            s = f"{f_val:.10f}".rstrip("0").rstrip(".")
            return s if s else "0"
        return f"{f_val:.4f}"
    except (ValueError, TypeError):
        return "NULL"


def canonical_market_data_serialize(row: Dict[str, Any], exact: bool = False) -> str:
    """
    Serializes a daily price row into a canonical normalized string.
    
    Fields included:
    symbol, date, open, high, low, close, adjusted_close, volume
    
    Normalization rules:
    - symbol: uppercase trimmed
    - date: YYYY-MM-DD
    - open, high, low, close: rounded to 4 decimal places (exact=False) or exact full precision (exact=True)
    - adjusted_close: rounded to 4 decimal places / full precision or 'NULL'
    - volume: integer string
    """
    symbol = str(row.get("symbol", "")).strip().upper()
    date = str(row.get("date", "")).strip()[:10]
    
    def norm_int(val: Any) -> str:
        if val is None or str(val).strip().upper() == "NULL" or str(val).strip() == "":
            return "NULL"
        try:
            return f"{int(val)}"
        except (ValueError, TypeError):
            return "NULL"

    open_str = _norm_float(row.get("open"), exact=exact)
    high_str = _norm_float(row.get("high"), exact=exact)
    low_str = _norm_float(row.get("low"), exact=exact)
    close_str = _norm_float(row.get("close"), exact=exact)
    adj_close_str = _norm_float(row.get("adjusted_close"), exact=exact)
    vol_str = norm_int(row.get("volume"))

    return f"{symbol}|{date}|{open_str}|{high_str}|{low_str}|{close_str}|{adj_close_str}|{vol_str}"


def canonical_market_data_hash(records: Sequence[Dict[str, Any]], exact: bool = False) -> str:
    """
    Computes a deterministic SHA-256 checksum over a collection of market data rows.
    Sorts all rows canonically by (symbol, date).
    """
    lines = [canonical_market_data_serialize(r, exact=exact) for r in records]
    lines.sort()
    canonical_payload = "\n".join(lines)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest().upper()


def canonical_exact_market_data_hash(records: Sequence[Dict[str, Any]]) -> str:
    """Exact bit-level migration integrity hash without 4-decimal rounding."""
    return canonical_market_data_hash(records, exact=True)


def canonical_indicator_serialize(row: Dict[str, Any], exact: bool = False) -> str:
    """
    Serializes a technical indicator row into a canonical normalized string.
    Fields: symbol, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score
    """
    symbol = str(row.get("symbol", "")).strip().upper()
    date = str(row.get("date", "")).strip()[:10]

    fields = [
        symbol,
        date,
        _norm_float(row.get("rsi"), exact=exact),
        _norm_float(row.get("macd"), exact=exact),
        _norm_float(row.get("macd_signal"), exact=exact),
        _norm_float(row.get("ema_20"), exact=exact),
        _norm_float(row.get("ema_50"), exact=exact),
        _norm_float(row.get("ema_200"), exact=exact),
        _norm_float(row.get("macd_histogram"), exact=exact),
        _norm_float(row.get("atr_14"), exact=exact),
        _norm_float(row.get("technical_score"), exact=exact),
    ]
    return "|".join(fields)


def canonical_indicator_hash(records: Sequence[Dict[str, Any]], exact: bool = False) -> str:
    lines = [canonical_indicator_serialize(r, exact=exact) for r in records]
    lines.sort()
    canonical_payload = "\n".join(lines)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest().upper()


def canonical_exact_indicator_hash(records: Sequence[Dict[str, Any]]) -> str:
    return canonical_indicator_hash(records, exact=True)


def canonical_financial_vintage_serialize(row: Dict[str, Any], exact: bool = False) -> str:
    """
    Serializes a financial vintage row into a canonical normalized string.
    Includes all core financial metrics, provenance, verification status, and research eligibility.
    """
    symbol = str(row.get("symbol", "")).strip().upper()
    quarter = str(row.get("quarter", "")).strip().upper()
    v_seq = str(row.get("version_sequence", "1")).strip()
    
    def norm_str(val: Any) -> str:
        if val is None or str(val).strip().upper() == "NULL" or str(val).strip() == "":
            return "NULL"
        return str(val).strip()

    fields = [
        symbol,
        quarter,
        v_seq,
        norm_str(row.get("period_start_date")),
        norm_str(row.get("period_end_date")),
        norm_str(row.get("verification_status")),
        norm_str(row.get("research_eligibility")),
        norm_str(row.get("publication_timestamp")),
        norm_str(row.get("publication_date")),
        norm_str(row.get("effective_trading_date")),
        norm_str(row.get("filing_scope")),
        norm_str(row.get("accounting_standard")),
        _norm_float(row.get("revenue"), exact=exact),
        _norm_float(row.get("operating_profit"), exact=exact),
        _norm_float(row.get("net_profit"), exact=exact),
        _norm_float(row.get("eps"), exact=exact),
        str(int(bool(row.get("is_banking_institution", 0)))),
        _norm_float(row.get("net_interest_income"), exact=exact),
        _norm_float(row.get("total_assets"), exact=exact),
        _norm_float(row.get("total_equity"), exact=exact),
        _norm_float(row.get("total_debt"), exact=exact),
        _norm_float(row.get("roe"), exact=exact),
        _norm_float(row.get("roce"), exact=exact),
        _norm_float(row.get("debt_equity"), exact=exact),
        _norm_float(row.get("operating_margin"), exact=exact),
        _norm_float(row.get("net_margin"), exact=exact),
        norm_str(row.get("source_document_hash")),
        norm_str(row.get("source_document_url")),
    ]
    return "|".join(fields)


def canonical_financial_vintage_hash(records: Sequence[Dict[str, Any]], exact: bool = False) -> str:
    lines = [canonical_financial_vintage_serialize(r, exact=exact) for r in records]
    lines.sort()
    canonical_payload = "\n".join(lines)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest().upper()


def canonical_exact_financial_vintage_hash(records: Sequence[Dict[str, Any]]) -> str:
    return canonical_financial_vintage_hash(records, exact=True)


def canonical_quarantine_serialize(row: Dict[str, Any], exact: bool = False) -> str:
    """
    Serializes a quarantined financial record into a canonical normalized string.
    Preserves original_id and original_table for complete legacy provenance tracking.
    """
    symbol = str(row.get("symbol", "")).strip().upper()
    quarter = str(row.get("quarter", "")).strip().upper()

    def norm_str(val: Any) -> str:
        if val is None or str(val).strip().upper() == "NULL" or str(val).strip() == "":
            return "NULL"
        return str(val).strip()

    fields = [
        symbol,
        quarter,
        _norm_float(row.get("revenue"), exact=exact),
        _norm_float(row.get("net_profit"), exact=exact),
        _norm_float(row.get("eps"), exact=exact),
        _norm_float(row.get("roe"), exact=exact),
        _norm_float(row.get("roce"), exact=exact),
        _norm_float(row.get("debt_equity"), exact=exact),
        _norm_float(row.get("operating_margin"), exact=exact),
        _norm_float(row.get("net_margin"), exact=exact),
        norm_str(row.get("publication_date")),
        norm_str(row.get("quarantine_reason")),
        norm_str(row.get("original_id")),
        norm_str(row.get("original_table")),
    ]
    return "|".join(fields)


def canonical_quarantine_hash(records: Sequence[Dict[str, Any]], exact: bool = False) -> str:
    """Computes deterministic SHA-256 hash for quarantined legacy financial records."""
    lines = [canonical_quarantine_serialize(r, exact=exact) for r in records]
    lines.sort()
    canonical_payload = "\n".join(lines)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest().upper()


def canonical_exact_quarantine_hash(records: Sequence[Dict[str, Any]]) -> str:
    return canonical_quarantine_hash(records, exact=True)


# ==============================================================================
# THREE-CATEGORY CONFLICT RESOLUTION ENGINE
# ==============================================================================

class ConflictCategory:
    MISSING = "MISSING"         # Destination record does not exist -> Eligible for insert
    MATCHING = "MATCHING"       # Destination record exists with identical values -> Skip
    CONFLICTING = "CONFLICTING" # Destination record exists with different values -> Quarantine for owner review


def classify_market_record(
    src_row: Dict[str, Any],
    dst_row: Optional[Dict[str, Any]],
    tolerance: float = MARKET_PRICE_TOLERANCE
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Classifies a market data record into one of three categories:
    1. MISSING: dst_row is None
    2. MATCHING: dst_row matches src_row across open, high, low, close, volume within tolerance (default MARKET_PRICE_TOLERANCE = 1e-4)
    3. CONFLICTING: dst_row exists but differs significantly. Returns diff details.
    """
    if dst_row is None:
        return ConflictCategory.MISSING, None

    diffs = {}
    float_fields = ["open", "high", "low", "close"]
    for f in float_fields:
        s_val = src_row.get(f)
        d_val = dst_row.get(f)
        if s_val is None and d_val is None:
            continue
        if s_val is None or d_val is None:
            diffs[f] = {"source": s_val, "destination": d_val}
            continue
        try:
            if abs(float(s_val) - float(d_val)) > tolerance:
                diffs[f] = {"source": float(s_val), "destination": float(d_val)}
        except (ValueError, TypeError):
            diffs[f] = {"source": s_val, "destination": d_val}

    # Volume check
    s_vol = src_row.get("volume")
    d_vol = dst_row.get("volume")
    if s_vol is not None and d_vol is not None:
        try:
            if int(s_vol) != int(d_vol):
                diffs["volume"] = {"source": int(s_vol), "destination": int(d_vol)}
        except (ValueError, TypeError):
            diffs["volume"] = {"source": s_vol, "destination": d_vol}

    if diffs:
        return ConflictCategory.CONFLICTING, diffs
    return ConflictCategory.MATCHING, None


def classify_financial_record(
    src_row: Dict[str, Any],
    dst_row: Optional[Dict[str, Any]],
    tolerance: float = FINANCIAL_TOLERANCE
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Classifies a financial vintage record into one of three categories.
    Checks revenue, net_profit, eps within FINANCIAL_TOLERANCE (default 1e-4 = 0.0001 Cr = Rs. 1,000 resolution),
    and exact matches on publication_timestamp, verification_status, and document hash.
    """
    if dst_row is None:
        return ConflictCategory.MISSING, None

    diffs = {}
    # Compare key strings
    str_fields = [
        "verification_status", "research_eligibility", 
        "publication_timestamp", "effective_trading_date", 
        "source_document_hash"
    ]
    for sf in str_fields:
        s_val = str(src_row.get(sf, "")).strip()
        d_val = str(dst_row.get(sf, "")).strip()
        if s_val != d_val:
            diffs[sf] = {"source": s_val, "destination": d_val}

    # Compare key financial numbers
    num_fields = ["revenue", "net_profit", "eps"]
    for nf in num_fields:
        s_num = src_row.get(nf)
        d_num = dst_row.get(nf)
        if s_num is None and d_num is None:
            continue
        if s_num is None or d_num is None:
            diffs[nf] = {"source": s_num, "destination": d_num}
            continue
        try:
            if abs(float(s_num) - float(d_num)) > tolerance:
                diffs[nf] = {"source": float(s_num), "destination": float(d_num)}
        except (ValueError, TypeError):
            diffs[nf] = {"source": s_num, "destination": d_num}

    if diffs:
        return ConflictCategory.CONFLICTING, diffs
    return ConflictCategory.MATCHING, None


# ==============================================================================
# SYNTHETIC & PILOT RECORD CLASSIFICATION SPECIFICATION
# ==============================================================================

class SyntheticDisposition:
    PRESERVE = "PRESERVE"
    ISOLATE = "ISOLATE"
    CANDIDATE_FOR_REMOVAL = "CANDIDATE_FOR_REMOVAL"
    REQUIRES_OWNER_DECISION = "REQUIRES_OWNER_DECISION"


def classify_pilot_record(symbol: str) -> Dict[str, Any]:
    """
    Returns dependency-aware classification for pilot records in Neon.
    Never executes a delete.
    """
    sym = symbol.strip().upper()
    if sym == "BADSTOCK":
        return {
            "symbol": sym,
            "disposition": SyntheticDisposition.ISOLATE,
            "reason": "Inactive error-handling fixture (is_active=False). Zero price data. Isolatable without side-effects."
        }
    elif sym == "LIVE_TEST":
        return {
            "symbol": sym,
            "disposition": SyntheticDisposition.CANDIDATE_FOR_REMOVAL,
            "reason": "Test fixture created during Phase 5.3 manual testing. Contains 144 dead price/indicator rows."
        }
    elif sym.startswith("STOCK") and sym[5:].isdigit():
        return {
            "symbol": sym,
            "disposition": SyntheticDisposition.CANDIDATE_FOR_REMOVAL,
            "reason": "Pilot mock fixtures from Phase 4.1/4.2 data boundary test suite. Totaling 2,090 rows in prices and indicators."
        }
    elif sym == "TATAMOTORS":
        return {
            "symbol": sym,
            "disposition": SyntheticDisposition.REQUIRES_OWNER_DECISION,
            "reason": "Historical corporate action mapping: Tata Motors was reorganized into TMPV and TMCV. Requires owner business decision on whether to preserve historical ticker identity or remap."
        }
    else:
        return {
            "symbol": sym,
            "disposition": SyntheticDisposition.PRESERVE,
            "reason": "Authoritative universe equity."
        }
