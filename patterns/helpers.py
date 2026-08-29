"""Shared helpers for pattern detection."""
import numpy as np


def find_local_extrema(series, order=3, kind='min'):
    """Find local minima or maxima in a series.
    Returns list of (index, value) tuples.
    """
    vals = series.values if hasattr(series, 'values') else np.array(series)
    result = []
    for i in range(order, len(vals) - order):
        if kind == 'min':
            if vals[i] == min(vals[i - order: i + order + 1]):
                result.append((i, float(vals[i])))
        else:
            if vals[i] == max(vals[i - order: i + order + 1]):
                result.append((i, float(vals[i])))
    return result


def compute_stop_loss(breakout, structural_stop, atr, atr_multiplier=2.0, max_risk_pct=0.08):
    """Calculate stop loss: max of structural and ATR, capped at max_risk."""
    atr_stop = breakout - (atr * atr_multiplier)
    stop = max(structural_stop, atr_stop)
    max_stop = breakout * (1 - max_risk_pct)
    stop = max(stop, max_stop)

    risk_pct = (breakout - stop) / breakout
    if risk_pct > max_risk_pct:
        stop = breakout * (1 - max_risk_pct)
        risk_pct = max_risk_pct
    return stop, risk_pct


def compute_targets(breakout, measured_move, target_1_pct=0.5, target_2_pct=1.0):
    """Calculate T1 and T2 from measured move."""
    t1 = breakout + (measured_move * target_1_pct)
    t2 = breakout + (measured_move * target_2_pct)
    return t1, t2


def determine_status(cmp, breakout, df, near_pct=0.05, watch_pct=0.15):
    """Determine BREAKOUT/NEAR/WATCH status with momentum check."""
    dist = (breakout - cmp) / cmp
    rising = check_momentum(df)

    if cmp >= breakout:
        return 'BREAKOUT'
    elif dist <= near_pct and rising:
        return 'NEAR'
    elif dist <= near_pct and not rising:
        return None  # falling away
    elif dist <= watch_pct and rising:
        return 'WATCH'
    else:
        return None


def check_momentum(df):
    """5D close > 10D close (stock rising)."""
    if len(df) < 10:
        return True
    close_5d = df['Close'].rolling(5).mean().iloc[-1]
    close_10d = df['Close'].rolling(10).mean().iloc[-1]
    return close_5d > close_10d
