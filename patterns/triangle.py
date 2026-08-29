"""
Triangle Pattern Detection — Ascending & Symmetrical.

Ascending Triangle:
- Flat resistance (multiple highs within 2.5% of each other)
- Rising lows (each swing low higher than previous)
- Price near flat resistance = breakout imminent

Symmetrical Triangle:
- Lower highs + higher lows (both converging to apex)
- Price near apex = breakout imminent
"""
import numpy as np
from .helpers import find_local_extrema, compute_stop_loss, compute_targets, determine_status


def detect_ascending_triangle(df, atr_multiplier=2.0, max_risk_pct=0.08,
                              target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    if df is None or len(df) < 40:
        return None

    try:
        min_bars = 30
        df_slice = df.tail(min_bars + 20)
        highs = df_slice['High'].values
        lows = df_slice['Low'].values
        cmp = float(df_slice['Close'].iloc[-1])

        peaks = find_local_extrema(df_slice['High'], order=5, kind='max')
        troughs = find_local_extrema(df_slice['Low'], order=5, kind='min')

        if len(peaks) < 2 or len(troughs) < 2:
            return None

        # Flat resistance: last 2-3 peaks within 2.5%
        recent_peaks = peaks[-3:] if len(peaks) >= 3 else peaks[-2:]
        peak_vals = [p[1] for p in recent_peaks]
        resistance = float(np.mean(peak_vals))

        if max(peak_vals) / min(peak_vals) > 1.025:
            return None

        # Rising lows
        recent_troughs = troughs[-3:] if len(troughs) >= 3 else troughs[-2:]
        trough_vals = [t[1] for t in recent_troughs]
        if not all(trough_vals[i] < trough_vals[i + 1]
                   for i in range(len(trough_vals) - 1)):
            return None

        # Price near resistance (within 5%)
        if cmp < resistance * 0.95 or cmp > resistance * 1.05:
            return None

        breakout = resistance
        support = float(trough_vals[-1])
        structural_stop = support
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (breakout - support)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        height = resistance - float(trough_vals[0])
        target_1, target_2 = compute_targets(breakout, height, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Ascending Triangle',
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


def detect_symmetrical_triangle(df, atr_multiplier=2.0, max_risk_pct=0.08,
                                target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    if df is None or len(df) < 40:
        return None

    try:
        min_bars = 30
        df_slice = df.tail(min_bars + 20)
        highs = df_slice['High'].values
        lows = df_slice['Low'].values
        cmp = float(df_slice['Close'].iloc[-1])

        peaks = find_local_extrema(df_slice['High'], order=5, kind='max')
        troughs = find_local_extrema(df_slice['Low'], order=5, kind='min')

        if len(peaks) < 2 or len(troughs) < 2:
            return None

        # Lower highs
        recent_peaks = peaks[-3:] if len(peaks) >= 3 else peaks[-2:]
        peak_vals = [p[1] for p in recent_peaks]
        if not all(peak_vals[i] > peak_vals[i + 1]
                   for i in range(len(peak_vals) - 1)):
            return None

        # Higher lows
        recent_troughs = troughs[-3:] if len(troughs) >= 3 else troughs[-2:]
        trough_vals = [t[1] for t in recent_troughs]
        if not all(trough_vals[i] < trough_vals[i + 1]
                   for i in range(len(trough_vals) - 1)):
            return None

        resistance = float(peak_vals[-1])
        support = float(trough_vals[-1])
        midpoint = (resistance + support) / 2

        # Price near apex (within 8%)
        if abs(cmp - midpoint) / midpoint > 0.08:
            return None

        breakout = resistance
        structural_stop = support
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (breakout - structural_stop)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        height = float(peak_vals[0]) - float(trough_vals[0])
        target_1, target_2 = compute_targets(breakout, height * 0.75, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Symmetrical Triangle',
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
