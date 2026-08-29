from config.settings import *

def detect_breakout(df):
    if df is None or len(df) < MIN_CANDLES:
        return None

    highs = df['High'].tail(LOOKBACK_PERIOD)
    lows = df['Low'].tail(LOOKBACK_PERIOD)

    resistance = float(highs.max())
    support = float(lows.min())

    current_price = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])

    avg_volume = float(df['Volume'].tail(VOLUME_LOOKBACK).mean())
    current_volume = float(df['Volume'].iloc[-1])

    # -----------------------
    # 🔥 BREAKOUT CONDITIONS
    # -----------------------
    breakout = current_price > resistance * 1.002
    strong_breakout = current_price > resistance * 1.03   # NEW (momentum)
    near_resistance = current_price >= resistance * 0.92

    # -----------------------
    # 🔥 VOLUME LOGIC
    # -----------------------
    volume_spike = current_volume > VOLUME_MULTIPLIER * avg_volume
    volume_rising = current_volume > df['Volume'].iloc[-2]
    volume_ok = volume_spike or volume_rising or True  # Allow breakouts without volume

    # -----------------------
    # 🔥 FALSE BREAKOUT FILTER
    # -----------------------
    if current_price < resistance and prev_close < resistance:
        return None

    # -----------------------
    # 🔥 STATUS LOGIC
    # -----------------------
    if strong_breakout and volume_ok:
        status = "MOMENTUM_BREAKOUT"
    elif breakout and volume_ok:
        status = "BREAKOUT"
    elif near_resistance:
        status = "NEAR"
    else:
        return None

    # -----------------------
    # 🔥 STOP LOSS
    # -----------------------
    recent_low = float(df['Low'].tail(5).min())
    stop_loss = recent_low * 0.98

    if stop_loss >= current_price:
        return None

    # -----------------------
    # 🔥 TARGET
    # -----------------------
    range_size = resistance - support

    target = min(
        resistance + range_size * 0.5,
        resistance * 1.12
    )

    return {
        "pattern": "Resistance Breakout",
        "cmp": current_price,
        "breakout": resistance,
        "stop_loss": stop_loss,
        "target": target,
        "volume": volume_ok,
        "status": status
    }