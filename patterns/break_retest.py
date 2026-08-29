"""
Break & Retest Pattern Detection

Logic:
1. Find a key resistance level broken in last 5-25 bars (with volume)
2. Price pulled back to retest that broken level (now acting as support)
3. Current price sitting near the retest zone — entry opportunity
"""

import numpy as np


def detect_break_retest(df, lookback=60):
    if df is None or len(df) < lookback + 10:
        return None

    try:
        closes  = df['Close'].values
        highs   = df['High'].values
        lows    = df['Low'].values
        volumes = df['Volume'].values
        n       = len(df)

        cmp      = float(closes[-1])
        avg_vol  = float(np.mean(volumes[-20:]))

        # Scan for a breakout in the last 5-25 bars
        for breakout_bar in range(n - 25, n - 5):
            if breakout_bar < lookback:
                continue

            # Resistance = highest high in the 40 bars BEFORE the breakout
            resistance = float(np.max(highs[breakout_bar - 40: breakout_bar]))

            bar_close  = float(closes[breakout_bar])
            bar_vol    = float(volumes[breakout_bar])

            # Breakout: closed above resistance with volume surge
            if bar_close < resistance * 1.01:
                continue
            if bar_vol < avg_vol * 1.3:
                continue

            # After breakout: price must have pulled back toward resistance
            post_low = float(np.min(lows[breakout_bar:]))
            retest_zone_top = resistance * 1.03
            retest_zone_bot = resistance * 0.97

            if post_low > retest_zone_top:
                continue  # never came back to retest
            if post_low < retest_zone_bot * 0.95:
                continue  # went too far below — failed retest

            # Current price must be near the retest zone (not run away already)
            if cmp > resistance * 1.08:
                continue  # already ran too far above
            if cmp < retest_zone_bot:
                continue  # sitting below resistance — retest failed

            # Stop below the retest low with small buffer
            stop_loss  = post_low * 0.98
            risk_amt   = cmp - stop_loss
            if risk_amt <= 0:
                continue

            # Target: measured move = distance from pre-breakout base to resistance
            base_low   = float(np.min(lows[breakout_bar - 40: breakout_bar]))
            move       = resistance - base_low
            target     = resistance + move

            if target <= cmp:
                continue

            rr = round((target - cmp) / risk_amt, 2)
            if rr < 1.0:
                continue

            return {
                "pattern":   "Break & Retest",
                "cmp":       cmp,
                "breakout":  round(resistance, 2),
                "stop_loss": round(stop_loss, 2),
                "target":    round(target, 2),
                "volume":    bar_vol > avg_vol * 1.5,
                "status":    "RETEST" if cmp <= resistance * 1.03 else "NEAR",
            }

    except Exception:
        return None

    return None
