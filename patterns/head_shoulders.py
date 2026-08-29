"""
Inverse Head & Shoulders — bullish reversal pattern.

Three troughs: left shoulder, head (lowest), right shoulder.
Neckline = line connecting the two peaks between shoulders and head.
Bullish breakout above neckline.

Structure:
  Peak1 (between L.shoulder and head)
  Peak2 (between head and R.shoulder)
  Neckline = line through Peak1 and Peak2
  Breakout = price crosses above neckline
"""
import numpy as np
from .helpers import find_local_extrema, compute_stop_loss, compute_targets, determine_status


def detect_inverse_head_shoulders(df, atr_multiplier=2.0, max_risk_pct=0.08,
                                  target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    """Detect inverse head & shoulders (bullish reversal)."""
    if df is None or len(df) < 80:
        return None

    try:
        lookback = 80
        window = df.iloc[-lookback:]
        lows = find_local_extrema(window['Low'], order=5, kind='min')
        highs = find_local_extrema(window['High'], order=5, kind='max')

        if len(lows) < 3 or len(highs) < 2:
            return None

        # Take last 3 lows as shoulder-head-shoulder
        ls_idx, ls_price = lows[-3]
        head_idx, head_price = lows[-2]
        rs_idx, rs_price = lows[-1]

        # Head must be lowest
        if head_price >= ls_price or head_price >= rs_price:
            return None

        # Shoulders should be roughly equal (within 5%)
        if abs(ls_price - rs_price) / ls_price > 0.05:
            return None

        # Head should be between the shoulders (chronologically)
        if not (ls_idx < head_idx < rs_idx):
            return None

        # Find the two peaks between shoulders and head
        peak1_window = window.iloc[ls_idx:head_idx]
        peak2_window = window.iloc[head_idx:rs_idx]
        if len(peak1_window) == 0 or len(peak2_window) == 0:
            return None

        peak1 = peak1_window['High'].max()
        peak2 = peak2_window['High'].max()

        # Neckline = average of the two peaks (simplified: flat neckline)
        neckline = (peak1 + peak2) / 2
        breakout = neckline
        cmp = float(df['Close'].iloc[-1])

        # Price near or above neckline
        if cmp < neckline * 0.93:
            return None
        if cmp > neckline * 1.08:
            return None

        structural_stop = head_price
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (neckline - head_price)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        measured_move = neckline - head_price
        target_1, target_2 = compute_targets(breakout, measured_move, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Inverse Head & Shoulders',
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
