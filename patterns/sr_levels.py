"""
S&R Horizontal Level Detection

Logic:
1. Find price zones where price has touched/reversed multiple times (3+)
2. Current price must be near a key S&R level
3. If price is above the level — it's support (buy on retest)
4. If price is below the level — it's resistance (buy on breakout)
"""

import numpy as np


def _find_sr_zones(highs, lows, closes, tolerance=0.02):
    """Find horizontal zones touched 3+ times."""
    all_levels = list(highs) + list(lows)
    zones = []

    for level in all_levels:
        # Count how many times price touched this zone
        touches = sum(
            1 for h, l in zip(highs, lows)
            if l <= level * (1 + tolerance) and h >= level * (1 - tolerance)
        )
        if touches >= 3:
            zones.append(level)

    if not zones:
        return []

    # Merge nearby zones (within 1.5%)
    zones = sorted(set(round(z, 2) for z in zones))
    merged = [zones[0]]
    for z in zones[1:]:
        if z > merged[-1] * 1.015:
            merged.append(z)
        else:
            merged[-1] = (merged[-1] + z) / 2  # average nearby levels

    return merged


def detect_sr_levels(df, lookback=60):
    if df is None or len(df) < lookback:
        return None

    try:
        df_slice = df.tail(lookback)
        highs  = df_slice['High'].values
        lows   = df_slice['Low'].values
        closes = df_slice['Close'].values
        vols   = df_slice['Volume'].values

        cmp     = float(closes[-1])
        avg_vol = float(np.mean(vols[-20:]))
        cur_vol = float(vols[-1])

        zones = _find_sr_zones(highs, lows, closes)
        if not zones:
            return None

        # Find the nearest S&R zone to current price
        nearest = min(zones, key=lambda z: abs(z - cmp))
        dist_pct = abs(nearest - cmp) / nearest

        # Must be within 4% of the level
        if dist_pct > 0.04:
            return None

        # Determine if support or resistance
        if cmp >= nearest:
            # Price above level = support retest
            setup_type = "S&R Support"
            stop_loss  = nearest * 0.97
            # Target = distance to next resistance zone above
            above_zones = [z for z in zones if z > nearest * 1.03]
            target = float(above_zones[0]) if above_zones else cmp * 1.10
        else:
            # Price below level = resistance breakout
            setup_type = "S&R Breakout"
            stop_loss  = cmp * 0.97
            target = nearest + (nearest - float(min(lows[-20:])))

        risk_amt = cmp - stop_loss
        if risk_amt <= 0 or target <= cmp:
            return None

        rr = round((target - cmp) / risk_amt, 2)
        if rr < 1.0:
            return None

        return {
            "pattern":   setup_type,
            "cmp":       cmp,
            "breakout":  round(nearest, 2),
            "stop_loss": round(stop_loss, 2),
            "target":    round(target, 2),
            "volume":    cur_vol > avg_vol * 1.2,
            "status":    "NEAR",
        }

    except Exception:
        return None
