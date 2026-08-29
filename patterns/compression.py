import numpy as np

def detect_compression(df):
    if df is None or len(df) < 80:
        return None

    highs = df['High'].tail(40)
    lows = df['Low'].tail(40)
    closes = df['Close']
    volumes = df['Volume']

    current_price = float(closes.iloc[-1])

    # -----------------------
    # 🔥 BETTER RESISTANCE (clustered)
    # -----------------------
    resistance = float(np.percentile(highs.tail(30), 95))

    # -----------------------
    # 🔥 HIGHER LOWS (robust)
    # -----------------------
    recent_lows = lows.tail(10).values

    slope = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]

    higher_lows = slope > 0  # upward bias instead of strict sequence

    # -----------------------
    # 🔥 COMPRESSION (true tightening)
    # -----------------------
    range_10 = highs.tail(10).max() - lows.tail(10).min()
    range_20 = highs.tail(20).max() - lows.tail(20).min()

    volatility = range_10 / current_price

    compression = (range_10 < range_20 * 0.75) and (volatility < 0.08)

    # -----------------------
    # 🔥 NEAR RESISTANCE
    # -----------------------
    distance = (resistance - current_price) / resistance
    near_resistance = 0 <= distance <= 0.06

    # -----------------------
    # 🔥 VOLUME BUILDUP (better)
    # -----------------------
    vol_short = volumes.tail(5).mean()
    vol_mid = volumes.tail(10).mean()
    vol_long = volumes.tail(20).mean()

    volume_build = (vol_short > vol_mid) and (vol_mid >= vol_long * 0.95)

    # -----------------------
    # 🔥 FILTER: avoid dead charts
    # -----------------------
    if volatility < 0.02:
        return None  # too flat

    # -----------------------
    # FINAL LOGIC
    # -----------------------
    if higher_lows and compression and near_resistance:

        # 🔥 IMPROVED STOP LOSS (tighter)
        swing_low = lows.tail(5).min()
        structure_low = lows.tail(10).quantile(0.3)

        stop_loss = float(min(swing_low, structure_low) * 0.99)

        if stop_loss >= current_price:
            return None

        # 🔥 REALISTIC TARGET
        target = float(resistance * 1.08)

        return {
            "pattern": "Higher-Low Compression",
            "cmp": current_price,
            "breakout": resistance,
            "stop_loss": stop_loss,
            "target": target,
            "volume": volume_build,
            "status": "PRE_BREAKOUT"
        }

    return None