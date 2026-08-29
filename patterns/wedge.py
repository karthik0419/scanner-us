"""
G9 — Falling / Descending Wedge breakout (bullish).

Defining features (Zensartech 2023-06 chart):
  - Series of LOWER highs forming a descending upper trendline
  - Lows that are roughly FLAT or also descending but with a SHALLOWER slope
    (the two lines converge, lower line above or close to the upper's slope)
  - Pattern is BULLISH on breakout above the upper trendline

This is the bullish-reversal counterpart to the descending triangle
(which the production scanner ignores).
"""
import numpy as np


def _swing_highs(highs, window=3):
    return [(i, float(highs[i])) for i in range(window, len(highs) - window)
            if highs[i] == max(highs[i - window: i + window + 1])]


def _swing_lows(lows, window=3):
    return [(i, float(lows[i])) for i in range(window, len(lows) - window)
            if lows[i] == min(lows[i - window: i + window + 1])]


def _linfit(points):
    """Return (slope, intercept) through (x, y) pairs. None if degenerate."""
    if len(points) < 2: return None
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    if xs.max() == xs.min(): return None
    m, c = np.polyfit(xs, ys, 1)
    return float(m), float(c)


def _detect_one(df, window):
    if df is None or len(df) < window + 5:
        return None
    s = df.tail(window).reset_index(drop=True)
    highs = s['High'].values
    lows  = s['Low'].values
    closes = s['Close'].values
    cmp_ = float(closes[-1])

    peaks   = _swing_highs(highs)
    troughs = _swing_lows(lows)
    if len(peaks) < 2 or len(troughs) < 2:
        return None

    up = _linfit(peaks[-4:] if len(peaks) >= 4 else peaks)
    lo = _linfit(troughs[-4:] if len(troughs) >= 4 else troughs)
    if up is None or lo is None:
        return None

    up_slope, up_int = up
    lo_slope, lo_int = lo

    # Upper line must descend (slope clearly negative)
    if up_slope >= 0:
        return None

    # Lower line must descend slower (or be ~flat / rising slightly)
    # i.e. converging from above
    if lo_slope <= up_slope:           # diverging or parallel
        return None

    # Range at start must be wider than at end (converging)
    start_x = peaks[0][0]
    end_x   = len(s) - 1
    width_start = (up_slope * start_x + up_int) - (lo_slope * start_x + lo_int)
    width_end   = (up_slope * end_x   + up_int) - (lo_slope * end_x   + lo_int)
    if width_start <= 0 or width_end <= 0 or width_end >= width_start:
        return None

    # Upper line value at "today"
    upper_today = up_slope * end_x + up_int
    lower_today = lo_slope * end_x + lo_int

    if cmp_ >= upper_today * 1.005:
        status = "BREAKOUT"
    elif cmp_ >= upper_today * 0.97:
        status = "NEAR"
    elif cmp_ >= upper_today * 0.92:
        status = "WATCH"
    else:
        return None

    # Target: full height of the wedge at its widest, projected up
    target    = upper_today + width_start
    stop_loss = lower_today * 0.98
    if stop_loss >= cmp_:
        return None

    return {
        "pattern":   "Descending Wedge",
        "cmp":       cmp_,
        "breakout":  round(upper_today, 2),
        "stop_loss": round(stop_loss, 2),
        "target":    round(target, 2),
        "volume":    False,
        "status":    status,
        "upper_slope": round(up_slope, 3),
        "lower_slope": round(lo_slope, 3),
        "convergence": round(width_end / width_start, 2),
        "window":      window,
    }


def detect_descending_wedge(df):
    best = None
    for w in [40, 60, 80, 120, 160]:
        r = _detect_one(df, w)
        if r:
            # prefer tighter convergence (smaller width_end/width_start)
            if best is None or r["convergence"] < best["convergence"]:
                best = r
    return best
