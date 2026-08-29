def detect_retest(df):
    if df is None or len(df) < 60:
        return None

    # Recent structure
    recent_high = df['High'].tail(20).max()
    recent_lows = df['Low'].tail(5)

    current_price = float(df['Close'].iloc[-1])
    avg_volume = float(df['Volume'].tail(20).mean())
    current_volume = float(df['Volume'].iloc[-1])

    # Check breakout happened (relaxed)
    breakout_happened = df['Close'].tail(10).max() > recent_high * 0.95

    # Retest zone (wider)
    retest_zone = current_price >= recent_high * 0.94

    # No breakdown (relaxed)
    holding_support = recent_lows.min() >= recent_high * 0.90

    # Bounce signal
    bounce = current_price > df['Close'].iloc[-2]

    volume_ok = current_volume > avg_volume

    if breakout_happened and retest_zone and holding_support:
        return {
            "pattern": "Breakout Retest",
            "cmp": current_price,
            "breakout": float(recent_high),
            "stop_loss": float(recent_lows.min() * 0.98),
            "target": float(current_price * 1.08),
            "volume": volume_ok,
            "status": "RETEST"
        }

    return None