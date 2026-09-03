import pandas as pd
import numpy as np

from backend.logic.explanation.technical_explanation import (
    explain_rsi,
    explain_macd,
    explain_trend,
    explain_volume,
    explain_technical_factors
)

def test_explain_rsi_positive():
    row = pd.Series({"rsi": 55.0, "rsi_score": 30.0})
    res = explain_rsi(row)
    assert res["sentiment"] == "positive"
    assert res["metric"] == "RSI"

def test_explain_rsi_negative_oversold():
    row = pd.Series({"rsi": 25.0, "rsi_score": 10.0})
    res = explain_rsi(row)
    assert res["sentiment"] == "negative"
    assert "oversold" in res["interpretation"]

def test_explain_rsi_negative_overbought():
    row = pd.Series({"rsi": 85.0, "rsi_score": 10.0})
    res = explain_rsi(row)
    assert res["sentiment"] == "negative"
    assert "overbought" in res["interpretation"]

def test_explain_rsi_neutral():
    row = pd.Series({"rsi": 75.0, "rsi_score": 20.0})
    res = explain_rsi(row)
    assert res["sentiment"] == "neutral"

def test_explain_rsi_missing():
    row = pd.Series({"rsi": np.nan, "rsi_score": np.nan})
    res = explain_rsi(row)
    assert res["sentiment"] == "missing"
    assert res["value"] == "Unavailable"

def test_explain_macd_positive():
    row = pd.Series({"macd": 1.5, "signal": 1.0, "histogram": 0.5, "macd_score": 30.0})
    res = explain_macd(row)
    assert res["sentiment"] == "positive"
    assert res["metric"] == "MACD"

def test_explain_macd_negative():
    row = pd.Series({"macd": -1.0, "signal": -0.5, "macd_score": 8.0})
    res = explain_macd(row)
    assert res["sentiment"] == "negative"

def test_explain_macd_missing():
    row = pd.Series({"macd": np.nan, "signal": np.nan, "macd_score": np.nan})
    res = explain_macd(row)
    assert res["sentiment"] == "missing"

def test_explain_trend_positive():
    row = pd.Series({"close": 150.0, "ema20": 140.0, "ema50": 130.0, "ema200": 100.0, "trend_score": 20.0})
    res = explain_trend(row)
    assert res["sentiment"] == "positive"

def test_explain_trend_negative():
    row = pd.Series({"close": 90.0, "ema20": 140.0, "ema50": 130.0, "ema200": 150.0, "trend_score": 0.0})
    res = explain_trend(row)
    assert res["sentiment"] == "negative"

def test_explain_trend_missing():
    row = pd.Series({"close": 90.0, "ema20": np.nan, "ema50": np.nan, "ema200": np.nan, "trend_score": np.nan})
    res = explain_trend(row)
    assert res["sentiment"] == "missing"

def test_explain_volume_positive():
    row = pd.Series({"volume_score": 20.0})
    res = explain_volume(row)
    assert res["sentiment"] == "positive"

def test_explain_volume_negative():
    row = pd.Series({"volume_score": 0.0})
    res = explain_volume(row)
    assert res["sentiment"] == "negative"

def test_explain_volume_missing():
    row = pd.Series({"volume_score": np.nan})
    res = explain_volume(row)
    assert res["sentiment"] == "missing"

def test_explain_technical_factors():
    df = pd.DataFrame([
        {"rsi": 55.0, "rsi_score": 30.0, "macd": 1.5, "signal": 1.0, "histogram": 0.5, "macd_score": 30.0, "close": 150.0, "ema20": 140.0, "ema50": 130.0, "ema200": 100.0, "trend_score": 20.0, "volume_score": 20.0}
    ])
    factors = explain_technical_factors(df)
    assert len(factors) == 4
    for f in factors:
        assert f["sentiment"] == "positive"
