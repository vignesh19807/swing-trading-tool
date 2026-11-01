"""
AUDIT-043 Experimental Setup Modules
===================================
Contains standalone, isolated prototypes of:
1. MomentumBreakoutSetup (Setup A)
2. SupportPullbackSetup (Setup B)
3. DualSetupArbitrator (Priority conflict resolver)

These prototypes do NOT modify production engines.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


class MomentumBreakoutSetup:
    """
    Experimental prototype for Setup A: Momentum Breakout.
    
    Hypothesis:
    Stocks breaking out above recent resistance levels with strong momentum
    (RSI 55-75, positive MACD histogram) and expanding volume continue their
    directional move.
    """
    
    SETUP_ID = "MOMENTUM_BREAKOUT_SETUP"
    
    def __init__(
        self,
        lookback_bars: int = 20,
        rsi_min: float = 55.0,
        rsi_max: float = 75.0,
        volume_multiplier: float = 1.20,
        entry_atr_multiplier: float = 0.50,
        stop_atr_multiplier: float = 0.75,
        target_atr_multiplier: float = 2.0,
        min_rr_ratio: float = 1.50
    ):
        self.lookback_bars = lookback_bars
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.volume_multiplier = volume_multiplier
        self.entry_atr_multiplier = entry_atr_multiplier
        self.stop_atr_multiplier = stop_atr_multiplier
        self.target_atr_multiplier = target_atr_multiplier
        self.min_rr_ratio = min_rr_ratio

    def evaluate(
        self,
        symbol: str,
        evaluation_date: str,
        df_hist: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Evaluate breakout setup strictly using history up to evaluation_date.
        df_hist must be sorted chronologically and include columns:
        ['date', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'macd_histogram', 'ema_20', 'ema_50', 'atr_14']
        """
        res = {
            "setup_id": self.SETUP_ID,
            "symbol": symbol,
            "evaluation_date": evaluation_date,
            "is_qualified": False,
            "rejection_reason": None,
            "breakout_level": None,
            "entry_lower": None,
            "entry_upper": None,
            "stop_loss": None,
            "target": None,
            "risk": None,
            "reward": None,
            "risk_reward_ratio": None,
            "market_price": None
        }

        if df_hist is None or len(df_hist) < self.lookback_bars + 1:
            res["rejection_reason"] = "INSUFFICIENT_HISTORY"
            return res

        curr_bar = df_hist.iloc[-1]
        res["market_price"] = float(curr_bar["close"])

        # Check for necessary indicators
        for col in ["close", "high", "low", "volume", "rsi", "macd_histogram", "ema_20", "ema_50", "atr_14"]:
            if col not in curr_bar or pd.isna(curr_bar[col]):
                res["rejection_reason"] = f"MISSING_INDICATOR_{col.upper()}"
                return res

        close = float(curr_bar["close"])
        high = float(curr_bar["high"])
        low = float(curr_bar["low"])
        vol = float(curr_bar["volume"])
        rsi = float(curr_bar["rsi"])
        macd_hist = float(curr_bar["macd_histogram"])
        ema20 = float(curr_bar["ema_20"])
        ema50 = float(curr_bar["ema_50"])
        atr = float(curr_bar["atr_14"])

        if atr <= 0:
            res["rejection_reason"] = "NON_POSITIVE_ATR"
            return res

        # 1. Trend & Momentum Qualification
        if not (close > ema20 > ema50):
            res["rejection_reason"] = "TREND_NOT_ALIGNED"
            return res

        if not (self.rsi_min <= rsi <= self.rsi_max):
            res["rejection_reason"] = "RSI_OUT_OF_MOMENTUM_RANGE"
            return res

        if macd_hist <= 0:
            res["rejection_reason"] = "NON_POSITIVE_MACD_HISTOGRAM"
            return res

        # 2. Breakout Level Verification (highest close of previous lookback_bars)
        prev_closes = df_hist["close"].iloc[-(self.lookback_bars + 1):-1]
        breakout_level = float(prev_closes.max())
        res["breakout_level"] = breakout_level

        # Price must be at or breaking above breakout level
        if close < (breakout_level - 0.10 * atr):
            res["rejection_reason"] = "PRICE_BELOW_BREAKOUT_LEVEL"
            return res

        # 3. Volume Expansion
        prev_vols = df_hist["volume"].iloc[-(self.lookback_bars + 1):-1]
        vol_sma = float(prev_vols.mean())
        if vol < (self.volume_multiplier * vol_sma):
            res["rejection_reason"] = "INSUFFICIENT_VOLUME_EXPANSION"
            return res

        # 4. Entry Zone Geometry: [Breakout Level, Breakout Level + 0.50 * ATR]
        entry_lower = breakout_level
        entry_upper = breakout_level + (self.entry_atr_multiplier * atr)
        res["entry_lower"] = round(entry_lower, 4)
        res["entry_upper"] = round(entry_upper, 4)

        if not (entry_lower <= close <= entry_upper):
            res["rejection_reason"] = "PRICE_OUTSIDE_BREAKOUT_ZONE"
            return res

        # 5. Stop Loss & Target Calculation
        # Stop loss below low of candle or breakout level
        stop_loss = min(low, breakout_level) - (self.stop_atr_multiplier * atr)
        # Cap max risk per share at 1.5 ATR
        if (close - stop_loss) > (1.50 * atr):
            stop_loss = close - (1.50 * atr)

        if stop_loss >= close:
            res["rejection_reason"] = "INVALID_STOP_LOSS"
            return res

        # Volatility expansion target
        risk = close - stop_loss
        target = close + max(self.target_atr_multiplier * atr, 2.0 * risk)
        reward = target - close
        rr = reward / risk if risk > 0 else 0.0

        res["stop_loss"] = round(stop_loss, 4)
        res["target"] = round(target, 4)
        res["risk"] = round(risk, 4)
        res["reward"] = round(reward, 4)
        res["risk_reward_ratio"] = round(rr, 4)

        if rr < self.min_rr_ratio:
            res["rejection_reason"] = "INSUFFICIENT_RISK_REWARD"
            return res

        res["is_qualified"] = True
        res["rejection_reason"] = None
        return res


class SupportPullbackSetup:
    """
    Experimental prototype for Setup B: Support Pullback.
    
    Hypothesis:
    Stocks in a major secular uptrend (Close > EMA200, EMA50 > EMA200) pulling back
    into verified support with oversold/exhausting momentum (RSI 30-48) offer high-expectancy
    reversal entries.
    """
    
    SETUP_ID = "SUPPORT_PULLBACK_SETUP"
    
    def __init__(
        self,
        rsi_min: float = 30.0,
        rsi_max: float = 48.0,
        entry_atr_multiplier: float = 0.50,
        stop_atr_multiplier: float = 1.00,
        min_rr_ratio: float = 1.50
    ):
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.entry_atr_multiplier = entry_atr_multiplier
        self.stop_atr_multiplier = stop_atr_multiplier
        self.min_rr_ratio = min_rr_ratio

    def evaluate(
        self,
        symbol: str,
        evaluation_date: str,
        df_hist: pd.DataFrame,
        nearest_support: Optional[Dict[str, Any]],
        nearest_resistance: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate pullback setup strictly using history up to evaluation_date.
        """
        res = {
            "setup_id": self.SETUP_ID,
            "symbol": symbol,
            "evaluation_date": evaluation_date,
            "is_qualified": False,
            "rejection_reason": None,
            "support_level": None,
            "entry_lower": None,
            "entry_upper": None,
            "stop_loss": None,
            "target": None,
            "risk": None,
            "reward": None,
            "risk_reward_ratio": None,
            "market_price": None
        }

        if df_hist is None or len(df_hist) < 20:
            res["rejection_reason"] = "INSUFFICIENT_HISTORY"
            return res

        curr_bar = df_hist.iloc[-1]
        res["market_price"] = float(curr_bar["close"])

        # Check indicators
        for col in ["close", "open", "high", "low", "rsi", "macd_histogram", "ema_50", "ema_200", "atr_14"]:
            if col not in curr_bar or pd.isna(curr_bar[col]):
                res["rejection_reason"] = f"MISSING_INDICATOR_{col.upper()}"
                return res

        close = float(curr_bar["close"])
        open_p = float(curr_bar["open"])
        low = float(curr_bar["low"])
        rsi = float(curr_bar["rsi"])
        macd_hist = float(curr_bar["macd_histogram"])
        ema50 = float(curr_bar["ema_50"])
        ema200 = float(curr_bar["ema_200"])
        atr = float(curr_bar["atr_14"])

        if atr <= 0:
            res["rejection_reason"] = "NON_POSITIVE_ATR"
            return res

        # 1. Macro Trend Filter (Secular uptrend)
        if not (close > ema200 and ema50 > ema200):
            res["rejection_reason"] = "MACRO_TREND_NOT_BULLISH"
            return res

        # 2. Oversold / Exhaustion Filter
        if not (self.rsi_min <= rsi <= self.rsi_max):
            res["rejection_reason"] = "RSI_NOT_IN_PULLBACK_RANGE"
            return res

        # 3. Support Validation
        if not nearest_support or "level" not in nearest_support or nearest_support["level"] is None:
            res["rejection_reason"] = "NO_VALID_SUPPORT"
            return res

        support_level = float(nearest_support["level"])
        res["support_level"] = support_level

        # 4. Entry Zone Geometry: [Support Level, Support Level + 0.50 * ATR]
        entry_lower = support_level
        entry_upper = support_level + (self.entry_atr_multiplier * atr)
        res["entry_lower"] = round(entry_lower, 4)
        res["entry_upper"] = round(entry_upper, 4)

        if not (entry_lower <= close <= entry_upper):
            res["rejection_reason"] = "PRICE_OUTSIDE_ENTRY_ZONE"
            return res

        # 5. Bullish Reversal Confirmation (e.g. green candle or hammer)
        if close < open_p and (close - low) < (0.5 * (curr_bar["high"] - low)):
            res["rejection_reason"] = "NO_BULLISH_REVERSAL_CONFIRMATION"
            return res

        # 6. Stop Loss & Target Calculation
        support_zone_low = float(nearest_support.get("zone_low", support_level))
        stop_loss = support_zone_low - (self.stop_atr_multiplier * atr)
        if stop_loss >= close:
            res["rejection_reason"] = "STOP_ABOVE_CURRENT_PRICE"
            return res

        if nearest_resistance and "zone_low" in nearest_resistance and nearest_resistance["zone_low"] is not None:
            target = float(nearest_resistance["zone_low"])
        else:
            target = close + (2.0 * atr)

        if target <= close:
            res["rejection_reason"] = "TARGET_BELOW_CURRENT_PRICE"
            return res

        risk = close - stop_loss
        reward = target - close
        rr = reward / risk if risk > 0 else 0.0

        res["stop_loss"] = round(stop_loss, 4)
        res["target"] = round(target, 4)
        res["risk"] = round(risk, 4)
        res["reward"] = round(reward, 4)
        res["risk_reward_ratio"] = round(rr, 4)

        if rr < self.min_rr_ratio:
            res["rejection_reason"] = "INSUFFICIENT_RISK_REWARD_RATIO"
            return res

        res["is_qualified"] = True
        res["rejection_reason"] = None
        return res


class DualSetupArbitrator:
    """
    Deterministic conflict arbitrator for combining Setup A and Setup B.
    """
    
    @staticmethod
    def arbitrate(
        setup_a_res: Dict[str, Any],
        setup_b_res: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Select winning setup deterministically without lookahead.
        """
        a_qual = setup_a_res.get("is_qualified", False)
        b_qual = setup_b_res.get("is_qualified", False)

        if not a_qual and not b_qual:
            return None, "NEITHER_SETUP_QUALIFIED"
        if a_qual and not b_qual:
            return setup_a_res, "SOLE_QUALIFIED_BREAKOUT"
        if b_qual and not a_qual:
            return setup_b_res, "SOLE_QUALIFIED_PULLBACK"

        # Both qualified: compare R:R
        rr_a = setup_a_res.get("risk_reward_ratio", 0.0) or 0.0
        rr_b = setup_b_res.get("risk_reward_ratio", 0.0) or 0.0

        if (rr_a - rr_b) > 0.25:
            return setup_a_res, "BREAKOUT_SUPERIOR_RR"
        if (rr_b - rr_a) > 0.25:
            return setup_b_res, "PULLBACK_SUPERIOR_RR"

        # Tied R:R: Breakout prioritized for momentum continuation
        return setup_a_res, "BREAKOUT_DEFAULT_PRIORITY"

