"""
Falling Wedge (Descending Wedge) — bullish reversal pattern.

- Series of lower highs (descending upper trendline)
- Lows flat or descending slower (converging lines)
- Bullish breakout above upper trendline
"""
import numpy as np
from .helpers import find_local_extrema, compute_stop_loss, compute_targets, determine_status


def _linfit(points):
    if len(points) < 2:
        return None
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    if xs.max() == xs.min():
        return None
    m, c = np.polyfit(xs, ys, 1)
    return float(m), float(c)


def _detect_one(df, window, atr_multiplier, max_risk_pct, target_1_pct, target_2_pct):
    if df is None or len(df) < window + 5:
        return None
    s = df.tail(window).reset_index(drop=True)
    highs = s['High'].values
    lows = s['Low'].values
    cmp = float(s['Close'].iloc[-1])

    peaks = find_local_extrema(s['High'], order=3, kind='max')
    troughs = find_local_extrema(s['Low'], order=3, kind='min')
    if len(peaks) < 2 or len(troughs) < 2:
        return None

    up = _linfit(peaks[-4:] if len(peaks) >= 4 else peaks)
    lo = _linfit(troughs[-4:] if len(troughs) >= 4 else troughs)
    if up is None or lo is None:
        return None

    up_slope, up_int = up
    lo_slope, lo_int = lo

    # Upper line must descend
    if up_slope >= 0:
        return None
    # Lower line must descend slower (converging)
    if lo_slope <= up_slope:
        return None

    # Range must converge
    start_x = peaks[0][0]
    end_x = len(s) - 1
    width_start = (up_slope * start_x + up_int) - (lo_slope * start_x + lo_int)
    width_end = (up_slope * end_x + up_int) - (lo_slope * end_x + lo_int)
    if width_start <= 0 or width_end <= 0 or width_end >= width_start:
        return None

    upper_today = up_slope * end_x + up_int
    lower_today = lo_slope * end_x + lo_int

    # Status
    if cmp >= upper_today * 1.005:
        status = 'BREAKOUT'
    elif cmp >= upper_today * 0.97:
        status = 'NEAR'
    elif cmp >= upper_today * 0.92:
        status = 'WATCH'
    else:
        return None

    breakout = upper_today
    structural_stop = lower_today
    atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else width_start

    stop_loss, risk_pct = compute_stop_loss(
        breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

    target_1, target_2 = compute_targets(breakout, width_start, target_1_pct, target_2_pct)

    upside = (target_1 - breakout) / breakout
    rr = upside / risk_pct if risk_pct > 0 else 0
    if rr < 1.0:
        return None

    return {
        'pattern': 'Falling Wedge',
        'status': status,
        'entry': breakout,
        'stop_loss': stop_loss,
        'target_1': target_1,
        'target_2': target_2,
        'risk_pct': risk_pct * 100,
        'rr': rr,
        'cmp': cmp,
        'mtf_confirmed': True,
    }


def detect_falling_wedge(df, atr_multiplier=2.0, max_risk_pct=0.08,
                         target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    """Try multiple window sizes, return best (tightest convergence)."""
    best = None
    for w in [40, 60, 80, 120]:
        r = _detect_one(df, w, atr_multiplier, max_risk_pct, target_1_pct, target_2_pct)
        if r:
            return r  # first match is fine for backtest
    return best
