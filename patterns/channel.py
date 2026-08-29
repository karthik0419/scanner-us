"""
Channel Breakout + Rectangle (horizontal channel).

Channel Breakout: stock breaks above a descending or ascending trendline channel.
Rectangle: stock breaks above a flat horizontal resistance after sideways consolidation.
"""
import numpy as np
from .helpers import find_local_extrema, compute_stop_loss, compute_targets, determine_status


def _fit_trendline(indices, values):
    coeffs = np.polyfit(indices, values, 1)
    return coeffs[0], coeffs[1]


def detect_channel_breakout(df, atr_multiplier=2.0, max_risk_pct=0.08,
                            target_1_pct=0.5, target_2_pct=1.0, df_weekly=None,
                            lookback=100):
    """Detect breakout from a descending channel (bullish reversal)."""
    if df is None or len(df) < lookback + 10:
        return None

    try:
        df_slice = df.tail(lookback + 10)
        highs = df_slice['High'].values
        lows = df_slice['Low'].values
        closes = df_slice['Close'].values
        n = len(df_slice)
        cmp = float(closes[-1])

        peaks = find_local_extrema(df_slice['High'], order=4, kind='max')
        troughs = find_local_extrema(df_slice['Low'], order=4, kind='min')

        if len(peaks) < 3 or len(troughs) < 3:
            return None

        h_slope, h_int = _fit_trendline([p[0] for p in peaks], [p[1] for p in peaks])
        l_slope, l_int = _fit_trendline([t[0] for t in troughs], [t[1] for t in troughs])

        # Descending channel (both slopes negative)
        if h_slope >= -0.05 or l_slope >= -0.05:
            return None

        upper_line = h_slope * (n - 1) + h_int
        lower_line = l_slope * (n - 1) + l_int
        channel_height = upper_line - lower_line
        if channel_height <= 0:
            return None

        # Price must be at or above upper line
        if cmp <= upper_line * 0.95:
            return None
        if cmp > upper_line * 1.08:
            return None  # too far above

        breakout = upper_line
        structural_stop = lower_line
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else channel_height

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        target_1, target_2 = compute_targets(breakout, channel_height, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        if cmp >= breakout:
            status = 'BREAKOUT'
        elif cmp >= breakout * 0.97:
            status = 'NEAR'
        elif cmp >= breakout * 0.92:
            status = 'WATCH'
        else:
            return None

        return {
            'pattern': 'Channel Breakout',
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


def detect_rectangle(df, atr_multiplier=2.0, max_risk_pct=0.08,
                     target_1_pct=0.5, target_2_pct=1.0, df_weekly=None,
                     lookback=40):
    """Detect rectangle (horizontal channel) breakout.

    Flat support + flat resistance + price breaking above resistance.
    """
    if df is None or len(df) < lookback + 10:
        return None

    try:
        df_slice = df.tail(lookback + 10)
        highs = df_slice['High'].values
        lows = df_slice['Low'].values
        cmp = float(df_slice['Close'].iloc[-1])

        peaks = find_local_extrema(df_slice['High'], order=4, kind='max')
        troughs = find_local_extrema(df_slice['Low'], order=4, kind='min')

        if len(peaks) < 2 or len(troughs) < 2:
            return None

        # Flat resistance: peaks within 3% of each other
        recent_peaks = peaks[-3:] if len(peaks) >= 3 else peaks[-2:]
        peak_vals = [p[1] for p in recent_peaks]
        resistance = float(np.mean(peak_vals))
        if max(peak_vals) / min(peak_vals) > 1.03:
            return None

        # Flat support: troughs within 3% of each other
        recent_troughs = troughs[-3:] if len(troughs) >= 3 else troughs[-2:]
        trough_vals = [t[1] for t in recent_troughs]
        support = float(np.mean(trough_vals))
        if max(trough_vals) / min(trough_vals) > 1.03:
            return None

        # Must be sideways (resistance and support roughly parallel)
        # Check slopes are near zero
        h_slope = np.polyfit([p[0] for p in recent_peaks], peak_vals, 1)[0]
        l_slope = np.polyfit([t[0] for t in recent_troughs], trough_vals, 1)[0]
        if abs(h_slope) > 0.1 * resistance or abs(l_slope) > 0.1 * support:
            return None

        # Channel height
        channel_height = resistance - support
        if channel_height / resistance < 0.05:
            return None  # too narrow

        # Price near or above resistance
        if cmp < resistance * 0.95:
            return None
        if cmp > resistance * 1.05:
            return None

        breakout = resistance
        structural_stop = support
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else channel_height

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        target_1, target_2 = compute_targets(breakout, channel_height, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Rectangle',
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
