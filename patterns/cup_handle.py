"""
Cup & Handle FULL tuned detector  (G1 + G2 + G3 + G4 + G5 + G7 + G10).

Stacks on top of cup_handle.py (v1) with:
  G3 — variable cup-length sweep (try multiple cup_bars, pick best by depth/shape score)
  G7 — BREAKOUT status requires volume_ok; otherwise demoted to NEAR
  G10 — 2-close confirmation: above breakout on current close only -> NEAR;
                              above breakout on current AND previous close -> BREAKOUT

Keeps the same return-dict shape as v1 plus:
  cup_bars_used   : int    (which cup length the sweep picked)
  prev_above_bk   : bool   (was previous close also above breakout? — used by G10)
"""


def _validate_cup_shape(cup_data):
    n = len(cup_data)
    if n < 9:
        return False
    low_idx = cup_data['Low'].argmin()
    return int(n * 0.10) <= low_idx <= int(n * 0.90)


def _fit_neckline(cup_data):
    n = len(cup_data)
    left_third  = cup_data['High'].iloc[: n // 3]
    right_third = cup_data['High'].iloc[2 * n // 3 :]
    left_x      = int(left_third.values.argmax())
    right_x     = int(right_third.values.argmax()) + 2 * n // 3
    left_high   = float(left_third.max())
    right_high  = float(right_third.max())
    if right_x == left_x:
        return 0.0, left_high, left_x, right_x, left_high, right_high
    slope = (right_high - left_high) / (right_x - left_x)
    intercept = left_high - slope * left_x
    return slope, intercept, left_x, right_x, left_high, right_high


def _try_one_cup_length(df, cup_bars, handle_bars,
                        min_depth, max_depth, near_pct, near_pct_watch,
                        max_slope_pct_per_bar,
                        handle_depth_ratio=0.90, volume_lookback=20):
    """One attempt with a specific cup_bars. Returns (result_dict, fit_score) or (None, 0).

    handle_depth_ratio: max handle depth as fraction of cup depth (default 0.90).
    volume_lookback: bars for average volume baseline (default 20).
    Both parameterised so weekly can use stricter values without affecting daily/monthly.
    """
    cup_bars = min(cup_bars, len(df) - handle_bars)
    if cup_bars < 15:
        return None, 0

    cup_data    = df.iloc[-(cup_bars + handle_bars) : -handle_bars]
    handle_data = df.tail(handle_bars)
    if cup_data.empty or handle_data.empty:
        return None, 0

    n = len(cup_data)
    cup_low = float(cup_data['Low'].min())

    slope, intercept, left_x, right_x, left_high, right_high = _fit_neckline(cup_data)
    cup_high = max(left_high, right_high)
    if cup_high <= 0:
        return None, 0
    slope_norm = slope / cup_high
    use_diagonal = slope_norm < -max_slope_pct_per_bar

    cup_depth = (cup_high - cup_low) / cup_high
    if not (min_depth <= cup_depth <= max_depth):
        return None, 0

    if not _validate_cup_shape(cup_data):
        return None, 0

    handle_high  = float(handle_data['High'].max())
    handle_low   = float(handle_data['Low'].min())
    current_price = float(df['Close'].iloc[-1])
    prev_close    = float(df['Close'].iloc[-2]) if len(df) >= 2 else current_price

    handle_position = (handle_low - cup_low) / (cup_high - cup_low)
    if handle_position < 0.25:
        return None, 0

    handle_depth = (handle_high - handle_low) / cup_high
    if handle_depth > cup_depth * handle_depth_ratio:
        return None, 0

    if use_diagonal:
        today_x = n + handle_bars - 1
        neckline_today = slope * today_x + intercept
        breakout_level = max(neckline_today, handle_high)
    else:
        breakout_level = max(right_high, handle_high)

    # Volume
    avg_volume     = float(df['Volume'].tail(volume_lookback).mean())
    current_volume = float(df['Volume'].iloc[-1])
    volume_ok      = current_volume > avg_volume * 1.2

    # Status with G7 + G10
    prev_above_bk = prev_close >= breakout_level
    if current_price >= breakout_level:
        # G10: need TWO consecutive closes above neckline
        # G7:  need volume_ok
        if prev_above_bk and volume_ok:
            status = "BREAKOUT"
        else:
            status = "NEAR"  # surfaced but not yet confirmed
    elif current_price >= breakout_level * (1 - near_pct):
        status = "NEAR"
    elif current_price >= breakout_level * (1 - near_pct_watch):
        status = "WATCH"
    else:
        return None, 0

    target = breakout_level + (cup_high - cup_low)
    stop_loss = handle_low * 0.98
    if stop_loss >= current_price:
        return None, 0

    # Fit score for the sweep: prefer deeper, well-shaped cups with the
    # current price as close to the neckline as possible.
    proximity = max(0, 1 - abs(current_price - breakout_level) / breakout_level / 0.20)
    fit_score = cup_depth * 50 + proximity * 50

    result = {
        "pattern":       "Cup & Handle",
        "cmp":           current_price,
        "breakout":      breakout_level,
        "stop_loss":     stop_loss,
        "target":        target,
        "volume":        volume_ok,
        "status":        status,
        "cup_depth_pct": round(cup_depth * 100, 1),
        "neckline_slope_pct_per_bar": round(slope_norm * 100, 4),
        "neckline_kind": "descending" if slope_norm < -0.0005 else "flat",
        "cup_bars_used": cup_bars,
        "prev_above_bk": prev_above_bk,
        # For chart annotation
        "cup_start_idx":    len(df) - cup_bars - handle_bars,
        "cup_end_idx":      len(df) - handle_bars - 1,
        "handle_start_idx": len(df) - handle_bars,
        "handle_end_idx":   len(df) - 1,
        "cup_low":          round(cup_low, 2),
        "cup_high":         round(cup_high, 2),
    }
    return result, fit_score


def _detect(df, cup_lengths, handle_bars, min_depth, max_depth,
            near_pct, near_pct_watch, min_bars,
            max_slope_pct_per_bar=0.0005,
            handle_depth_ratio=0.90, volume_lookback=20):
    if df is None or len(df) < min_bars:
        return None
    best, best_score = None, -1
    for cb in cup_lengths:
        res, score = _try_one_cup_length(
            df, cb, handle_bars,
            min_depth, max_depth,
            near_pct, near_pct_watch,
            max_slope_pct_per_bar,
            handle_depth_ratio, volume_lookback,
        )
        if res and score > best_score:
            best, best_score = res, score
    return best


# ---------- Daily ----------
def detect_cup_handle(df):
    return _detect(
        df,
        cup_lengths    = [60, 90, 120, 180, 240],     # G3: sweep
        handle_bars    = 15,
        min_depth      = 0.12,
        max_depth      = 0.80,
        near_pct       = 0.08,
        near_pct_watch = 0.15,
        min_bars       = 140,
    )


# ---------- Weekly ----------
def detect_cup_handle_weekly(df_weekly):
    # v3 fix: tightened params based on backtest showing -0.56% expectancy.
    # Root cause: handle_bars=12 (3 months) allowed downtrends as "handles",
    # near_pct=0.15/0.25 generated premature entries far from breakout,
    # handle_depth_ratio=0.90 allowed handles as deep as the cup itself.
    # Fix aligns with Bulkowski: 1-4 week handles, shallow pullbacks,
    # tighter breakout proximity, 1-year volume baseline.
    result = _detect(
        df_weekly,
        cup_lengths    = [30, 45, 65, 90, 130],       # G3: sweep (up to ~30 months)
        handle_bars    = 4,                           # was 12 — 4 weeks per Bulkowski
        min_depth      = 0.15,
        max_depth      = 0.50,                        # was 0.90 — filter V-shaped cups
        near_pct       = 0.08,                        # was 0.15 — match daily tightness
        near_pct_watch = 0.15,                        # was 0.25 — match daily
        min_bars       = 40,
        handle_depth_ratio = 0.50,                    # was 0.90 — handle <= 50% of cup depth
        volume_lookback    = 52,                      # was 20 — 1-year baseline for weekly
    )
    if result:
        result["pattern"]   = "Cup & Handle"
        result["timeframe"] = "Weekly"
    return result
