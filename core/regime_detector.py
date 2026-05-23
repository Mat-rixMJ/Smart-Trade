"""
regime_detector.py — Professional Market Regime Detector
=============================================================
Detects: TREND | SIDEWAYS | CHOPPY
Calculates confidence score based on multiple indicators.
Now with Dynamic RR Suggestions.
=============================================================
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

def calculate_adx(df: pd.DataFrame, period: int = 14) -> tuple:
    """Calculates Average Directional Index (ADX) and +/- DI."""
    high = df["high"]
    low  = df["low"]
    close = df["close"]

    plus_dm  = high.diff()
    minus_dm = low.diff().abs()
    plus_dm[plus_dm < 0]   = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[plus_dm < minus_dm]  = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr      = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10)
    dx       = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    adx      = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, plus_di, minus_di

def choppiness_index(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs()
    ], axis=1).max(axis=1)
    
    atr_sum = tr.rolling(period).sum()
    hh = df["high"].rolling(period).max()
    ll = df["low"].rolling(period).min()
    chop = 100 * np.log10(atr_sum / (hh - ll + 1e-10)) / np.log10(period)
    return chop

def detect_regime(df: pd.DataFrame, verbose: bool = False) -> Dict[str, Any]:
    """
    Analyzes price action to determine the current market environment.
    Returns dynamic RR targets based on market strength.
    """
    if len(df) < 20:
        return {"regime": "UNKNOWN", "action": "SIT_OUT", "reason": "Not enough data", "suggested_rr": 2.0}

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    adx, plus_di, minus_di = calculate_adx(df)
    chop = choppiness_index(df)
    
    adx_val = float(adx.iloc[-1])
    chop_val = float(chop.iloc[-1])
    pdi_val = float(plus_di.iloc[-1])
    mdi_val = float(minus_di.iloc[-1])

    # Dynamic RR Logic
    if adx_val > 30 and chop_val < 45:
        regime = "STRONG_TREND"
        suggested_rr = 2.5
        partial_rr = 1.2
        action = "RUN_TREND"
    elif adx_val > 20 and chop_val < 55:
        regime = "NORMAL_TREND"
        suggested_rr = 2.0
        partial_rr = 1.0
        action = "RUN_TREND"
    elif chop_val > 61.8:
        regime = "CHOPPY"
        suggested_rr = 1.2
        partial_rr = 0.8
        action = "SIT_OUT"
    else:
        regime = "SIDEWAYS"
        suggested_rr = 1.5
        partial_rr = 0.8
        action = "RUN_SIDEWAYS"

    result = {
        "regime": regime,
        "adx": round(adx_val, 2),
        "chop_index": round(chop_val, 2),
        "action": action,
        "suggested_rr": suggested_rr,
        "partial_rr": partial_rr,
        "reason": f"ADX: {adx_val:.1f}, Chop: {chop_val:.1f}"
    }

    if verbose:
        log.info(f"📊 Market Regime: {regime} | RR Target: {suggested_rr}x")

    return result
