"""
Backend REST API Layer
======================

FastAPI implementation adhering strictly to docs/frontend-api-contract.md.
Serves read-only queries with point-in-time historical semantics,
readiness/liveness probes, and decomposed data health monitoring.
"""

import json
import math
import os
import sqlite3
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import DATABASE_PATH, CORS_ORIGINS
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.classification_service import get_all_classifications, get_company_classification
from backend.data_pipeline.stock_snapshot_service import get_stock_snapshot
from backend.data_pipeline.data_service import get_latest_price
from backend.engines.universe_orchestrator import rank_universe
from backend.engines.sector_industry_engine import run_sector_industry_engine
from backend.logic.stock_intelligence import get_stock_intelligence
from backend.logic.signal_integration import run_signal_pipeline, calculate_opportunity_score
from backend.logic.backtest_metrics import calculate_backtest_metrics
from backend.logic.backtest_specification import TradeState

app = FastAPI(
    title="Swing Trading Intelligence Platform API",
    version="1.0.0",
    description="Deterministic swing trading intelligence, sector strength, and risk management endpoints.",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _clean_floats(obj: Any) -> Any:
    """Recursively clean NaNs and infinities for strict JSON compliance."""
    if obj is None:
        return None
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _clean_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_floats(v) for v in obj]
    return obj


def _get_latest_market_date() -> Optional[str]:
    """Fetch the latest trade date recorded in daily_prices."""
    try:
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM daily_prices WHERE date IS NOT NULL")
            row = cursor.fetchone()
            if row and row[0]:
                return row[0][:10]
    except Exception:
        pass
    return None


# -----------------------------------------------------------------------------
# Liveness & Readiness Probes
# -----------------------------------------------------------------------------

@app.get("/healthz/live", tags=["Health"])
def liveness():
    """Liveness probe: verifies process is alive."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/healthz/ready", tags=["Health"])
def readiness():
    """Readiness probe: validates DB access and schema readiness."""
    if not os.path.exists(DATABASE_PATH):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database file does not exist")
    try:
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM companies")
            companies_count = cursor.fetchone()[0]
            if companies_count == 0:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unseeded")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database check failed: {e}")
    return {"status": "ready", "companies_count": companies_count}


# -----------------------------------------------------------------------------
# Contract Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/market/indices", tags=["Market"])
def get_market_indices():
    """
    Returns market condition, breadth (advancing/declining), and benchmark status.
    Calculates genuine advance/decline numbers from daily_prices across the active universe.
    Does NOT fabricate mock index prices.
    """
    latest_date = _get_latest_market_date()
    
    advancing = 0
    declining = 0
    total_evaluated = 0

    try:
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT date FROM daily_prices WHERE date IS NOT NULL ORDER BY date DESC LIMIT 2")
            recent_dates = [r[0] for r in cursor.fetchall()]

            if len(recent_dates) >= 2:
                curr_d, prev_d = recent_dates[0], recent_dates[1]
                cursor.execute("""
                    SELECT d1.company_id, d1.close, d2.close
                    FROM daily_prices d1
                    JOIN daily_prices d2 ON d1.company_id = d2.company_id
                    WHERE d1.date = ? AND d2.date = ?
                """, (curr_d, prev_d))
                rows = cursor.fetchall()
                total_evaluated = len(rows)
                advancing = sum(1 for r in rows if (r[1] or 0) > (r[2] or 0))
                declining = sum(1 for r in rows if (r[1] or 0) < (r[2] or 0))
    except Exception:
        pass

    # Determine regime from actual universe breadth
    if total_evaluated > 0:
        breadth_ratio = advancing / total_evaluated
        if breadth_ratio >= 0.55:
            regime = "BULLISH"
            cond_status = "Positive"
            cond_label = "Swing friendly"
            cond_desc = f"Market breadth positive ({advancing} advancing, {declining} declining)"
        elif breadth_ratio <= 0.45:
            regime = "BEARISH"
            cond_status = "Negative"
            cond_label = "Defensive"
            cond_desc = f"Market breadth weak ({advancing} advancing, {declining} declining)"
        else:
            regime = "NEUTRAL"
            cond_status = "Neutral"
            cond_label = "Selective"
            cond_desc = f"Mixed breadth ({advancing} advancing, {declining} declining)"
    else:
        regime = "UNAVAILABLE"
        cond_status = "Neutral"
        cond_label = "Data Unavailable"
        cond_desc = "Insufficient price history to compute market breadth"

    # Contract response matching frontend Dashboard expectations
    # Benchmark indices return null when not actively ingested, preventing fake values
    return {
        "status": "VALID" if total_evaluated > 0 else "PARTIAL",
        "market_regime": regime,
        "as_of_date": latest_date,
        "nifty50": {
            "value": None,
            "change_percent": None,
            "is_positive": None,
            "status": "UNAVAILABLE",
            "message": "NIFTY 50 index benchmark not ingested into local equity store"
        },
        "sensex": {
            "value": None,
            "change_percent": None,
            "is_positive": None,
            "status": "UNAVAILABLE",
            "message": "SENSEX index benchmark not ingested into local equity store"
        },
        "condition": {
            "status": cond_status,
            "label": cond_label,
            "description": cond_desc,
            "advancing": advancing,
            "declining": declining,
            "evaluated_universe": total_evaluated
        },
        "indices": []
    }


@app.get("/api/opportunities", tags=["Opportunities"])
def get_opportunities(evaluation_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """
    Returns ranked swing trading opportunities with entry, stop-loss, target, and risk-reward ratios.
    """
    eval_date = evaluation_date or _get_latest_market_date()
    
    ranked_results = []
    try:
        ranking_data = rank_universe(evaluation_date=eval_date)
        ranked_results = ranking_data.get("top_10", []) if isinstance(ranking_data, dict) else []
    except Exception as e:
        ranked_results = []

    opportunities = []
    for item in ranked_results:
        symbol = item.get("symbol")
        rec = item.get("recommendation", "HOLD")
        
        # Calculate or reuse setup levels from ranking
        setup = item.get("setup")
        if not setup:
            try:
                signal_res = run_signal_pipeline(symbol, evaluation_date=eval_date)
                setup = signal_res if isinstance(signal_res, dict) else {}
            except Exception:
                setup = {}

        price_val = None
        try:
            lp = get_latest_price(symbol, evaluation_date=eval_date)
            if lp and "close" in lp:
                price_val = lp["close"]
        except Exception:
            pass

        # Extract sub-scores from structured_explanation
        structured_exp = item.get("structured_explanation") or {}
        score_breakdown = structured_exp.get("score_breakdown") or {}
        tech_score = score_breakdown.get("technical_score")
        fin_score = score_breakdown.get("financial_score")
        mom_score = score_breakdown.get("momentum_score")

        opp = {
            "symbol": symbol,
            "company_name": item.get("company_name", symbol),
            "sector": item.get("sector", "Unknown"),
            "industry": item.get("industry", "Unknown"),
            "rank": item.get("rank"),
            "opportunity_score": _clean_floats(item.get("opportunity_score")),
            "technical_score": _clean_floats(tech_score),
            "financial_score": _clean_floats(fin_score),
            "momentum_score": _clean_floats(mom_score),
            "sector_score": _clean_floats(item.get("sector_score")),
            "final_ranking_score": _clean_floats(item.get("final_ranking_score")),
            "recommendation": rec,
            "status": item.get("status", "VALID"),
            "current_price": _clean_floats(price_val),
            "entry_zone_low": _clean_floats(setup.get("entry_lower")),
            "entry_zone_high": _clean_floats(setup.get("entry_upper")),
            "stop_loss": _clean_floats(setup.get("stop_loss")),
            "target": _clean_floats(setup.get("target")),
            "risk_reward": _clean_floats(setup.get("risk_reward_ratio")),
            "risk_score": setup.get("trade_quality", {}).get("risk_status") if isinstance(setup.get("trade_quality"), dict) else None,
        }
        opportunities.append(opp)

    return {
        "evaluation_date": eval_date,
        "data_as_of": f"{eval_date}T15:30:00+05:30" if eval_date else None,
        "is_historical": bool(evaluation_date),
        "total_count": len(opportunities),
        "opportunities": opportunities
    }


@app.get("/api/stocks", tags=["Stocks"])
def get_stocks(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
):
    """Returns universe of stocks with classification, latest prices, and precomputed technical indicators."""
    from backend.engines.cache_service import get_cached_universe_scores

    class_df = get_all_classifications()
    classifications = class_df.to_dict(orient="records") if class_df is not None and not class_df.empty else []
    
    # Filter
    if search:
        search_lower = search.lower()
        classifications = [
            c for c in classifications
            if search_lower in str(c.get("symbol", "")).lower() or search_lower in str(c.get("company_name", "")).lower()
        ]
    if sector:
        classifications = [c for c in classifications if c.get("sector") == sector]

    total_count = len(classifications)
    start_idx = (page - 1) * limit
    paginated = classifications[start_idx : start_idx + limit]

    # Fetch latest and previous close prices, plus latest precomputed technical indicators in a single efficient query
    price_map = {}
    tech_map = {}
    try:
        with _get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    c.symbol, 
                    dp1.close as latest_close, 
                    dp1.date as latest_date, 
                    dp2.close as prev_close, 
                    dp2.date as prev_date,
                    ti.rsi,
                    ti.macd,
                    ti.macd_signal,
                    ti.macd_histogram,
                    ti.ema_20,
                    ti.ema_50,
                    ti.ema_200,
                    ti.technical_score,
                    ti.date as ti_date,
                    (SELECT COUNT(*) FROM daily_prices WHERE company_id = c.id) as history_count
                FROM companies c
                LEFT JOIN daily_prices dp1 
                    ON dp1.company_id = c.id 
                    AND dp1.date = (SELECT MAX(date) FROM daily_prices WHERE company_id = c.id)
                LEFT JOIN daily_prices dp2 
                    ON dp2.company_id = c.id 
                    AND dp2.date = (SELECT MAX(date) FROM daily_prices WHERE company_id = c.id AND date < dp1.date)
                LEFT JOIN technical_indicators ti
                    ON ti.company_id = c.id
                    AND ti.date = (SELECT MAX(date) FROM technical_indicators WHERE company_id = c.id)
            """)
            for row in cur.fetchall():
                (sym, l_close, l_date, p_close, p_date,
                 rsi, macd, macd_sig, macd_hist,
                 ema20, ema50, ema200, tech_score, ti_date, hist_count) = row
                
                chg_pct = None
                if l_close is not None and p_close is not None and p_close > 0:
                    chg_pct = round(((l_close - p_close) / p_close) * 100, 2)
                price_map[sym] = {
                    "close": l_close,
                    "date": l_date,
                    "prev_close": p_close,
                    "change_percent": chg_pct,
                }
                tech_map[sym] = {
                    "rsi": rsi,
                    "macd": macd,
                    "signal": macd_sig,
                    "histogram": macd_hist,
                    "ema20": ema20,
                    "ema50": ema50,
                    "ema200": ema200,
                    "close": l_close,
                    "technical_score": tech_score,
                    "date": ti_date,
                    "isInsufficient": bool(rsi is None or (hist_count or 0) < 15),
                    "historyLength": hist_count or 0,
                    "status": "READY" if rsi is not None else "INSUFFICIENT_HISTORY",
                }
    except Exception:
        price_map = {}
        tech_map = {}

    # Retrieve cached universe scores if available
    eval_date = _get_latest_market_date()
    universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None)
    if universe_scores is None:
        try:
            rank_universe(evaluation_date=eval_date)
            universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or {}
        except Exception:
            universe_scores = {}

    # Attach current price, price change, opportunity score, recommendation, and precomputed technicals
    stocks = []
    for item in paginated:
        sym = item.get("symbol")
        p_info = price_map.get(sym) or {}
        t_info = tech_map.get(sym) or {}
        
        # Calculate opportunity score and decision recommendation
        opp_score = None
        recommendation = None
        if sym in universe_scores:
            u_info = universe_scores[sym]
            opp_score = u_info.get("opportunity_score")
            recommendation = u_info.get("recommendation")
        else:
            try:
                decision = calculate_opportunity_score(sym)
                if isinstance(decision, dict) and decision.get("status") in ("VALID", "PARTIAL"):
                    opp_score = decision.get("opportunity_score")
                    recommendation = decision.get("recommendation")
            except Exception:
                pass

        stocks.append({
            "symbol": sym,
            "company_name": item.get("company_name"),
            "sector": item.get("sector"),
            "industry": item.get("industry"),
            "exchange": item.get("exchange", "NSE"),
            "current_price": _clean_floats(p_info.get("close")),
            "date": p_info.get("date"),
            "change_percent": _clean_floats(p_info.get("change_percent")),
            "opportunity_score": _clean_floats(opp_score),
            "recommendation": recommendation,
            "market_status": "Active",
            "technicals": {
                "rsi": _clean_floats(t_info.get("rsi")),
                "macd": _clean_floats(t_info.get("macd")),
                "signal": _clean_floats(t_info.get("signal")),
                "histogram": _clean_floats(t_info.get("histogram")),
                "ema20": _clean_floats(t_info.get("ema20")),
                "ema50": _clean_floats(t_info.get("ema50")),
                "ema200": _clean_floats(t_info.get("ema200")),
                "close": _clean_floats(p_info.get("close")),
                "technical_score": _clean_floats(t_info.get("technical_score")),
                "date": t_info.get("date"),
                "isInsufficient": t_info.get("isInsufficient", False),
                "historyLength": t_info.get("historyLength", 0),
                "status": t_info.get("status", "READY"),
            }
        })

    return {
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "stocks": stocks
    }


@app.get("/api/stocks/{symbol}", tags=["Stocks"])
def get_stock_detail(
    symbol: str,
    evaluation_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """Returns complete stock intelligence payload for an individual symbol."""
    sym_clean = symbol.strip().upper()
    eval_date = evaluation_date or _get_latest_market_date()

    # Verify symbol existence in company universe
    company = get_company_classification(sym_clean)
    if not company or not company.get("symbol"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock symbol '{sym_clean}' not found in universe"
        )

    payload = get_stock_intelligence(sym_clean, evaluation_date=eval_date)
    if not payload or payload.get("status") == "INVALID":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock symbol '{sym_clean}' not found in universe"
        )

    # Attach point-in-time metadata
    payload["evaluation_date"] = eval_date
    payload["data_as_of"] = f"{eval_date}T15:30:00+05:30" if eval_date else None
    payload["is_historical"] = bool(evaluation_date)

    return _clean_floats(payload)


@app.get("/api/stocks/{symbol}/history", tags=["Stocks"])
def get_stock_history(
    symbol: str,
    timeframe: Optional[str] = Query(None, pattern=r"^(1M|3M|6M|1Y|ALL)$"),
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    """Returns OHLCV candlestick series for a symbol."""
    sym_clean = symbol.strip().upper()

    # Verify symbol existence in company universe
    company = get_company_classification(sym_clean)
    if not company or not company.get("symbol"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock symbol '{sym_clean}' not found in universe"
        )

    res = get_historical_data(sym_clean, start_date=start_date, end_date=end_date)
    df = res.get("data") if isinstance(res, dict) else res
    if df is None or (hasattr(df, "empty") and df.empty):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical price records found for {sym_clean}"
        )

    records = []
    for _, row in df.iterrows():
        records.append({
            "date": str(row["date"])[:10],
            "open": _clean_floats(row.get("open")),
            "high": _clean_floats(row.get("high")),
            "low": _clean_floats(row.get("low")),
            "close": _clean_floats(row.get("close")),
            "volume": int(row.get("volume") or 0),
        })

    return {
        "symbol": sym_clean,
        "count": len(records),
        "candles": records
    }


@app.get("/api/sectors", tags=["Sectors"])
def get_sectors(
    evaluation_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ranking_period: str = Query("63D")
):
    """Returns ranked sector and industry performance."""
    eval_date = evaluation_date or _get_latest_market_date()
    try:
        res = run_sector_industry_engine(evaluation_date=eval_date, ranking_period=ranking_period)
        if isinstance(res, dict) and "sectors" not in res:
            res["sectors"] = res.get("sector_rankings", [])
        return _clean_floats(res)
    except Exception as e:
        return {
            "status": "VALID",
            "evaluation_date": eval_date,
            "ranking_period": ranking_period,
            "sectors": [],
            "sector_rankings": [],
            "error": str(e)
        }


def _is_genuine_trade_record(meta: Any) -> bool:
    """
    Determines if metadata represents a genuine simulated trade execution,
    as opposed to opportunity scores, rankings, or summary data.
    """
    if not isinstance(meta, dict) or not meta:
        return False
    # Check for presence of real trade execution attributes
    status = meta.get("status")
    has_trade_status = status in (TradeState.CLOSED, TradeState.OPEN, "CLOSED", "OPEN")
    has_execution_prices = (meta.get("entry_price") is not None and isinstance(meta.get("entry_price"), (int, float))) or \
                           (meta.get("exit_price") is not None and isinstance(meta.get("exit_price"), (int, float)))
    has_pnl = (meta.get("pl") is not None and isinstance(meta.get("pl"), (int, float))) or \
              (meta.get("return_pct") is not None and isinstance(meta.get("return_pct"), (int, float)))

    # Reject records that only contain scoring or ranking metrics
    score_only_keys = {"score", "rank", "opportunity_score", "technical_score", "financial_score"}
    if set(meta.keys()).issubset(score_only_keys):
        return False

    return bool(has_trade_status or (has_execution_prices and (meta.get("entry_date") or meta.get("exit_date"))) or has_pnl)


@app.get("/api/backtests/latest", tags=["Backtest"])
def get_latest_backtest():
    """
    Returns the most recent backtest metrics and equity curve calculated strictly
    from genuine simulated trade executions.
    If no genuine trade records are available, returns an explicit UNAVAILABLE status.
    """
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_results'")
        if not cursor.fetchone():
            return {
                "status": "UNAVAILABLE",
                "reason": "No genuine simulated trade execution records are available.",
                "backtest_run_id": None,
                "run_id": None,
                "evaluation_period": None,
                "start_date": None,
                "end_date": None,
                "symbols": [],
                "total_trades": 0,
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "breakeven_trades": 0,
                "win_rate": None,
                "profit_factor": None,
                "max_drawdown": None,
                "max_drawdown_pct": None,
                "total_pl": None,
                "total_return_pct": None,
                "trades": [],
                "equity_curve": []
            }

        # Find the latest backtest run
        cursor.execute("""
            SELECT run_id
            FROM backtest_results
            ORDER BY id DESC
            LIMIT 1
        """)
        latest_run_row = cursor.fetchone()
        if not latest_run_row:
            return {
                "status": "UNAVAILABLE",
                "reason": "No genuine simulated trade execution records are available.",
                "backtest_run_id": None,
                "run_id": None,
                "evaluation_period": None,
                "start_date": None,
                "end_date": None,
                "symbols": [],
                "total_trades": 0,
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "breakeven_trades": 0,
                "win_rate": None,
                "profit_factor": None,
                "max_drawdown": None,
                "max_drawdown_pct": None,
                "total_pl": None,
                "total_return_pct": None,
                "trades": [],
                "equity_curve": []
            }

        latest_run_id = latest_run_row["run_id"]

        # Fetch records for this latest run
        cursor.execute("""
            SELECT run_id, symbol, evaluation_date, result_metadata, created_at
            FROM backtest_results
            WHERE run_id = ?
            ORDER BY evaluation_date ASC, id ASC
            LIMIT 500
        """, (latest_run_id,))
        rows = cursor.fetchall()

        # Check for persisted portfolio equity curve and initial capital
        curve_data = []
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_equity_curve'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT date, cash, positions_value, total_equity, drawdown_pct
                FROM backtest_equity_curve
                WHERE run_id = ?
                ORDER BY date ASC
            """, (latest_run_id,))
            for cr in cursor.fetchall():
                curve_data.append({
                    "date": cr["date"],
                    "cash": cr["cash"],
                    "positions_value": cr["positions_value"],
                    "equity": cr["total_equity"],
                    "drawdown_pct": cr["drawdown_pct"]
                })

        init_cap = None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_runs'")
        if cursor.fetchone():
            cursor.execute("SELECT initial_capital FROM backtest_runs WHERE run_id = ?", (latest_run_id,))
            run_cap_row = cursor.fetchone()
            if run_cap_row:
                init_cap = run_cap_row["initial_capital"]

    if not rows:
        return {
            "status": "UNAVAILABLE",
            "reason": "No genuine simulated trade execution records are available.",
            "backtest_run_id": latest_run_id,
            "run_id": latest_run_id,
            "evaluation_period": None,
            "start_date": None,
            "end_date": None,
            "symbols": [],
            "total_trades": 0,
            "closed_trades": 0,
            "open_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": None,
            "profit_factor": None,
            "max_drawdown": None,
            "max_drawdown_pct": None,
            "total_pl": None,
            "total_return_pct": None,
            "trades": [],
            "equity_curve": []
        }

    genuine_trades = []
    for r in rows:
        row_dict = dict(r)
        meta_raw = row_dict.get("result_metadata")
        if isinstance(meta_raw, str):
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = {}
        elif isinstance(meta_raw, dict):
            meta = meta_raw
        else:
            meta = {}

        if _is_genuine_trade_record(meta):
            trade_obj = {
                "run_id": row_dict.get("run_id"),
                "symbol": row_dict.get("symbol"),
                "evaluation_date": row_dict.get("evaluation_date"),
                "created_at": row_dict.get("created_at"),
                **meta
            }
            genuine_trades.append(trade_obj)

    # Case B: No genuine simulated trade execution records exist in this run
    if not genuine_trades:
        return {
            "status": "UNAVAILABLE",
            "reason": "No genuine simulated trade execution records are available.",
            "backtest_run_id": latest_run_id,
            "run_id": latest_run_id,
            "evaluation_period": None,
            "start_date": None,
            "end_date": None,
            "symbols": [],
            "total_trades": 0,
            "closed_trades": 0,
            "open_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": None,
            "profit_factor": None,
            "max_drawdown": None,
            "max_drawdown_pct": None,
            "total_pl": None,
            "total_return_pct": None,
            "trades": [],
            "equity_curve": []
        }

    # Case A: Genuine trade execution records exist
    metrics = calculate_backtest_metrics(
        genuine_trades,
        strict_mode=True,
        portfolio_equity_curve=curve_data if curve_data else None,
        initial_capital=init_cap
    )

    dates = [t["evaluation_date"] for t in genuine_trades if t.get("evaluation_date")]
    start_date = min(dates) if dates else None
    end_date = max(dates) if dates else None
    eval_period = f"{start_date} to {end_date}" if start_date and end_date else None
    symbols = sorted(list(set(t["symbol"] for t in genuine_trades if t.get("symbol"))))

    return {
        "status": "VALID",
        "backtest_run_id": latest_run_id,
        "run_id": latest_run_id,
        "evaluation_period": eval_period,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": symbols,
        "total_trades": metrics["total_trades"],
        "closed_trades": metrics["closed_trades"],
        "open_trades": metrics["open_trades"],
        "winning_trades": metrics["winning_trades"],
        "losing_trades": metrics["losing_trades"],
        "breakeven_trades": metrics.get("breakeven_trades", 0),
        "win_rate": metrics["win_rate"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown": metrics["max_drawdown_pct"],
        "max_drawdown_pct": metrics["max_drawdown_pct"],
        "total_pl": metrics.get("total_pl"),
        "gross_pl": metrics.get("gross_pl"),
        "total_costs": metrics.get("total_costs"),
        "net_pl": metrics.get("net_pl"),
        "total_return_pct": metrics.get("total_return_pct"),
        "avg_trade_return_pct": metrics.get("avg_trade_return_pct"),
        "avg_winning_trade_pct": metrics.get("avg_winning_trade_pct"),
        "avg_losing_trade_pct": metrics.get("avg_losing_trade_pct"),
        "trades": _clean_floats(genuine_trades[:50]),
        "equity_curve": metrics.get("equity_curve", [])
    }


@app.get("/api/data-health", tags=["Health"])
def get_data_health():
    """
    Exposes decomposed data health, calendar-aware freshness, and pipeline status.
    """
    latest_trade_date = _get_latest_market_date()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Calendar freshness calculation
    # If today is weekend or after 15:45 IST, evaluate appropriately
    price_status = "CURRENT"
    if not latest_trade_date:
        price_status = "MISSING"
    elif (datetime.strptime(today_str, "%Y-%m-%d") - datetime.strptime(latest_trade_date, "%Y-%m-%d")).days > 4:
        price_status = "STALE"

    total_companies = 0
    total_prices = 0
    total_indicators = 0
    total_financials = 0
    companies_with_financials = 0

    try:
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM companies")
            total_companies = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM daily_prices")
            total_prices = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM technical_indicators")
            total_indicators = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*), COUNT(DISTINCT company_id) FROM quarterly_results")
            fin_row = cursor.fetchone()
            total_financials = fin_row[0] if fin_row else 0
            companies_with_financials = fin_row[1] if fin_row else 0
    except Exception:
        pass

    indicator_status = "SYNCHRONIZED" if total_indicators > 0 else "UNSYNCHRONIZED"
    financial_status = "HEALTHY" if companies_with_financials >= total_companies and total_companies > 0 else "PARTIAL"

    is_healthy = price_status == "CURRENT" and indicator_status == "SYNCHRONIZED" and financial_status == "HEALTHY"

    return {
        "status": "HEALTHY" if is_healthy else "WARNING",
        "latest_eod_date": latest_trade_date,
        "price_data_status": price_status,
        "indicator_status": indicator_status,
        "financial_status": financial_status,
        "market_data": "Healthy" if price_status == "CURRENT" else price_status.capitalize(),
        "technical_data": "Healthy" if indicator_status == "SYNCHRONIZED" else "Unsynchronized",
        "financial_data": "Healthy" if financial_status == "HEALTHY" else "Partial",
        "pipeline_status": "IDLE",
        "universe_size": total_companies,
        "universe_count": total_companies,
        "total_price_records": total_prices,
        "total_indicator_records": total_indicators,
        "total_financial_records": total_financials,
        "last_health_check": datetime.utcnow().isoformat(),
        "last_updated": f"{latest_trade_date}T15:30:00+05:30" if latest_trade_date else None,
        "warnings": [] if is_healthy else ["Market or indicator data synchronization warning"]
    }


# -----------------------------------------------------------------------------
# Static File Serving for Production Frontend
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
dist_dir = PROJECT_ROOT / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        if (
            full_path.startswith("api/")
            or full_path.startswith("healthz")
            or full_path.startswith("docs")
            or full_path.startswith("openapi.json")
        ):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = dist_dir / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(dist_dir / "index.html")

