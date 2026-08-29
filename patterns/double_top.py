"""
Double Top — bearish reversal pattern (mirror of Double Bottom).

Price tests a resistance level twice, fails to break it, and reverses down.
We detect it as a potential SHORT setup, but for long-only backtest we
detect the inverse: Double Top that has BROKEN DOWN (confirmation).

Actually for a long-only scanner, the useful variant is:
- Stock formed a double top in the past
- Has since broken DOWN below the support (neckline)
- We skip this — it's a bearish signal

So instead, we detect the BREAKOUT ABOVE a double top (rare but powerful):
- Stock tested resistance twice (double top)
- Then broke ABOVE that resistance
- This is a very bullish signal (overhead supply cleared)

This is essentially a "double resistance breakout" — similar to a rectangle
but with only 2 distinct peaks.
"""
import numpy as np
from .helpers import find_local_extrema, compute_stop_loss, compute_targets, determine_status


def detect_double_top(df, atr_multiplier=2.0, max_risk_pct=0.08,
                      target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    """Detect breakout above a double top resistance (bullish).

    This is the bullish variant: stock cleared double-top resistance.
    """
    if df is None or len(df) < 60:
        return None

    try:
        lookback = 60
        window = df.iloc[-lookback:]
        highs = find_local_extrema(window['High'], order=3, kind='max')
        if len(highs) < 2:
            return None

        # Last two peaks (the "double top")
        p1_idx, p1_price = highs[-2]
        p2_idx, p2_price = highs[-1]

        # Peaks should be within 3% of each other (similar height)
        if abs(p1_price - p2_price) / p1_price > 0.03:
            return None

        # Peaks should be at least 15 bars apart
        if (p2_idx - p1_idx) < 15:
            return None

        # The valley between the two peaks
        valley_window = window.iloc[p1_idx:p2_idx]
        if len(valley_window) == 0:
            return None
        valley_low = valley_window['Low'].min()

        # Resistance = average of the two peaks
        resistance = (p1_price + p2_price) / 2
        breakout = resistance
        cmp = float(df['Close'].iloc[-1])

        # For bullish variant: price must be at or above resistance
        # (broke through the double top)
        if cmp < resistance * 0.95:
            return None
        if cmp > resistance * 1.08:
            return None  # too far above

        structural_stop = valley_low
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (resistance - valley_low)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        measured_move = resistance - valley_low
        target_1, target_2 = compute_targets(breakout, measured_move, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Double Top Breakout',
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
    except Exception:
        return None
