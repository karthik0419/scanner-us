"""
Triangle Pattern Detection — Ascending & Symmetrical

Ascending Triangle:
- Flat resistance (multiple highs within 2% of each other)
- Rising lows (each swing low higher than previous)
- Price near the flat resistance = breakout imminent

Symmetrical Triangle:
- Lower highs + higher lows (both converging to apex)
- Price near apex = breakout imminent
"""

import numpy as np


def _swing_highs(highs, window=5):
    """Find local swing highs."""
    peaks = []
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i - window: i + window + 1]):
            peaks.append((i, highs[i]))
    return peaks


def _swing_lows(lows, window=5):
    """Find local swing lows."""
    troughs = []
    for i in range(window, len(lows) - window):
        if lows[i] == min(lows[i - window: i + window + 1]):
            troughs.append((i, lows[i]))
    return troughs


def detect_ascending_triangle(df, min_bars=30):
    if df is None or len(df) < min_bars + 10:
        return None

    try:
        df_slice = df.tail(min_bars + 20)
        highs  = df_slice['High'].values
        lows   = df_slice['Low'].values
        closes = df_slice['Close'].values
        cmp    = float(closes[-1])

        peaks   = _swing_highs(highs)
        troughs = _swing_lows(lows)

        if len(peaks) < 2 or len(troughs) < 2:
            return None

        # Flat resistance: last 3 peaks within 2.5% of each other
        recent_peaks = peaks[-3:] if len(peaks) >= 3 else peaks[-2:]
        peak_vals    = [p[1] for p in recent_peaks]
        resistance   = float(np.mean(peak_vals))

        if max(peak_vals) / min(peak_vals) > 1.025:
            return None  # not flat enough

        # Rising lows: each trough higher than the previous
        recent_troughs = troughs[-3:] if len(troughs) >= 3 else troughs[-2:]
        trough_vals    = [t[1] for t in recent_troughs]

        if not all(trough_vals[i] < trough_vals[i + 1]
                   for i in range(len(trough_vals) - 1)):
            return None  # lows not rising

        # Price near resistance (within 5%) — breakout imminent
        if cmp < resistance * 0.95:
            return None
        if cmp > resistance * 1.05:
            return None  # already broke out

        support    = float(trough_vals[-1])
        stop_loss  = support * 0.98
        risk_amt   = cmp - stop_loss
        if risk_amt <= 0:
            return None

        # Target: height of triangle projected from breakout
        height    = resistance - float(trough_vals[0])
        target    = resistance + height
        rr        = round((target - cmp) / risk_amt, 2)

        if rr < 1.0:
            return None

        return {
            "pattern":   "Ascending Triangle",
            "cmp":       cmp,
            "breakout":  round(resistance, 2),
            "stop_loss": round(stop_loss, 2),
            "target":    round(target, 2),
            "volume":    False,
            "status":    "NEAR",
        }

    except Exception:
        return None


def detect_symmetrical_triangle(df, min_bars=30):
    if df is None or len(df) < min_bars + 10:
        return None

    try:
        df_slice = df.tail(min_bars + 20)
        highs  = df_slice['High'].values
        lows   = df_slice['Low'].values
        closes = df_slice['Close'].values
        cmp    = float(closes[-1])

        peaks   = _swing_highs(highs)
        troughs = _swing_lows(lows)

        if len(peaks) < 2 or len(troughs) < 2:
            return None

        # Lower highs
        recent_peaks  = peaks[-3:] if len(peaks) >= 3 else peaks[-2:]
        peak_vals     = [p[1] for p in recent_peaks]
        if not all(peak_vals[i] > peak_vals[i + 1]
                   for i in range(len(peak_vals) - 1)):
            return None

        # Higher lows
        recent_troughs = troughs[-3:] if len(troughs) >= 3 else troughs[-2:]
        trough_vals    = [t[1] for t in recent_troughs]
        if not all(trough_vals[i] < trough_vals[i + 1]
                   for i in range(len(trough_vals) - 1)):
            return None

        resistance = float(peak_vals[-1])
        support    = float(trough_vals[-1])
        midpoint   = (resistance + support) / 2

        # Price near apex (within 8% of midpoint)
        if abs(cmp - midpoint) / midpoint > 0.08:
            return None

        stop_loss = support * 0.98
        risk_amt  = cmp - stop_loss
        if risk_amt <= 0:
            return None

        # Target: height of triangle from breakout
        height = float(peak_vals[0]) - float(trough_vals[0])
        target = resistance + height * 0.75  # conservative 75% of height

        rr = round((target - cmp) / risk_amt, 2)
        if rr < 1.0:
            return None

        return {
            "pattern":   "Symmetrical Triangle",
            "cmp":       cmp,
            "breakout":  round(resistance, 2),
            "stop_loss": round(stop_loss, 2),
            "target":    round(target, 2),
            "volume":    False,
            "status":    "NEAR",
        }

    except Exception:
        return None


def detect_triangle(df):
    """Try ascending first (higher success rate), then symmetrical."""
    return detect_ascending_triangle(df) or detect_symmetrical_triangle(df)
