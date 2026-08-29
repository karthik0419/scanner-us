"""
Bull Flag & Pennant detection.

Bull Flag: sharp move up (flagpole) + small downward/sideways consolidation (flag) + breakout.
Pennant: sharp move up + converging consolidation + breakout.
"""
import numpy as np
from .helpers import compute_stop_loss, compute_targets, determine_status


def detect_bull_flag(df, atr_multiplier=2.0, max_risk_pct=0.08,
                     target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    """Detect bullish flag pattern."""
    if df is None or len(df) < 40:
        return None

    try:
        # Flagpole: 10-15 bars strong move up
        flagpole_period = min(15, len(df) - 20)
        flagpole_data = df.tail(flagpole_period + 10).head(flagpole_period)
        flagpole_start = float(flagpole_data['Close'].iloc[0])
        flagpole_end = float(flagpole_data['Close'].iloc[-1])
        flagpole_change = (flagpole_end - flagpole_start) / flagpole_start

        # Flagpole must be strong (10%+)
        if flagpole_change < 0.10:
            return None

        # Flag: last 5-10 bars consolidation
        flag_period = min(10, len(df) - flagpole_period)
        flag_data = df.tail(flag_period)
        cmp = float(df['Close'].iloc[-1])

        flag_high = float(flag_data['High'].max())
        flag_low = float(flag_data['Low'].min())
        flag_range = flag_high - flag_low

        # Flag should be tight (less than 8% range)
        if flag_range / flag_high > 0.08:
            return None

        # Flag should be slight pullback or sideways (not continuing up)
        flag_trend = (flag_data['Close'].iloc[-1] - flag_data['Close'].iloc[0]) / flag_data['Close'].iloc[0]
        if flag_trend > 0.03:
            return None

        breakout = flag_high
        structural_stop = flag_low
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (flag_range / 2)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        # Target: 60% of flagpole projected from breakout
        measured_move = flagpole_change * cmp * 0.6
        target_1, target_2 = compute_targets(breakout, measured_move, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Bull Flag',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk_pct': risk_pct * 100,
            'rr': rr,
            'cmp': cmp,
            'mtf_confirmed': True,  # checked by caller
        }
    except Exception:
        return None


def detect_pennant(df, atr_multiplier=2.0, max_risk_pct=0.08,
                   target_1_pct=0.5, target_2_pct=1.0, df_weekly=None):
    """Detect bullish pennant pattern."""
    if df is None or len(df) < 40:
        return None

    try:
        # Flagpole
        flagpole_period = min(15, len(df) - 20)
        flagpole_data = df.tail(flagpole_period + 10).head(flagpole_period)
        flagpole_start = float(flagpole_data['Close'].iloc[0])
        flagpole_end = float(flagpole_data['Close'].iloc[-1])
        flagpole_change = (flagpole_end - flagpole_start) / flagpole_start

        if flagpole_change < 0.10:
            return None

        # Pennant: converging consolidation
        pennant_period = min(10, len(df) - flagpole_period)
        pennant_data = df.tail(pennant_period)
        cmp = float(df['Close'].iloc[-1])

        highs = pennant_data['High'].values
        lows = pennant_data['Low'].values
        x = np.arange(len(highs))

        high_slope = np.polyfit(x, highs, 1)[0]
        low_slope = np.polyfit(x, lows, 1)[0]

        # Bullish pennant: highs sloping down, lows sloping up (converging)
        if not (high_slope < 0 and low_slope > 0):
            return None

        breakout = float(highs[-1])
        structural_stop = float(lows[-1])
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (breakout - structural_stop)

        stop_loss, risk_pct = compute_stop_loss(
            breakout, structural_stop, atr, atr_multiplier, max_risk_pct)

        measured_move = flagpole_change * cmp * 0.5
        target_1, target_2 = compute_targets(breakout, measured_move, target_1_pct, target_2_pct)

        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        if rr < 1.0:
            return None

        status = determine_status(cmp, breakout, df)
        if status is None:
            return None

        return {
            'pattern': 'Bull Pennant',
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
