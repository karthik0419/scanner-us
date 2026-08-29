"""
G8 — Tuned Double Bottom with full measured-move target.

Differences vs production double_top_bottom.py:
- Sweeps multiple window lengths (60 / 100 / 150 / 200 / 250 bars).
- Bottom-similarity tolerance relaxed from 2% to 10%
  (real charts often have a higher 2nd bottom — the "stronger" recovery).
- Target = peak + (peak - bottom)  — full measured move, not 50%.
- Adds WATCH (within 15% below neckline) and NEAR (within 5%) tiers.
"""


def _try_window(df, window):
    if len(df) < window + 5:
        return None, 0
    s = df.tail(window)
    n = len(s)

    # Bottom 1: lowest low in the first half
    half = n // 2
    b1_idx_local = int(s['Low'].iloc[:half].values.argmin())
    b1 = float(s['Low'].iloc[:half].min())

    # Bottom 2: lowest low in the second half
    b2_offset = half
    b2_idx_local = b2_offset + int(s['Low'].iloc[b2_offset:].values.argmin())
    b2 = float(s['Low'].iloc[b2_offset:].min())

    # Bottoms within 10% of each other (relaxed from 2%)
    if abs(b1 - b2) / max(b1, b2) > 0.10:
        return None, 0

    # Peak between the two bottoms = neckline
    if b2_idx_local <= b1_idx_local:
        return None, 0
    peak = float(s['High'].iloc[b1_idx_local:b2_idx_local].max())

    # Peak must be ≥ 12% above the bottoms (more conservative than prod's 5%)
    bottom = min(b1, b2)
    if (peak - bottom) / bottom < 0.12:
        return None, 0

    cmp_ = float(df['Close'].iloc[-1])
    breakout_level = peak

    if cmp_ >= breakout_level:
        status = "BREAKOUT"
    elif cmp_ >= breakout_level * 0.95:
        status = "NEAR"
    elif cmp_ >= breakout_level * 0.85:
        status = "WATCH"
    else:
        return None, 0

    # Must already be in recovery — at least 5% above last bottom
    if cmp_ < b2 * 1.05:
        return None, 0

    # FULL measured-move target  (prod used 50%)
    target    = breakout_level + (peak - bottom)
    stop_loss = b2 * 0.97

    if stop_loss >= cmp_:
        return None, 0

    score = (peak - bottom) / bottom * 100
    return {
        "pattern":   "Double Bottom",
        "cmp":       cmp_,
        "breakout":  round(breakout_level, 2),
        "stop_loss": round(stop_loss, 2),
        "target":    round(target, 2),
        "volume":    True,
        "status":    status,
        "window":    window,
        "bottom_1":  round(b1, 2),
        "bottom_2":  round(b2, 2),
        "neckline":  round(peak, 2),
    }, score


def detect_double_bottom(df):
    if df is None or len(df) < 60:
        return None
    best, best_score = None, -1
    for w in [60, 100, 150, 200, 250]:
        res, sc = _try_window(df, w)
        if res and sc > best_score:
            best, best_score = res, sc
    return best
