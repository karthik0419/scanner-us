def detect_flag_pennant(df):
    if df is None or len(df) < 40:
        return None
    
    # Flag/Pennant pattern: strong move followed by consolidation
    # Look for flagpole (strong move) + flag (consolidation)
    
    # Flagpole: last 10-15 days strong move
    flagpole_period = min(15, len(df) - 20)
    flagpole_data = df.tail(flagpole_period)
    
    flagpole_start = float(flagpole_data['Close'].iloc[0])
    flagpole_end = float(flagpole_data['Close'].iloc[-1])
    flagpole_change = abs(flagpole_end - flagpole_start) / flagpole_start
    
    # Flagpole should be strong move (10%+)
    if flagpole_change < 0.10:
        return None
    
    # Flag: last 5-10 days consolidation
    flag_period = min(10, len(df) - flagpole_period)
    flag_data = df.tail(flag_period)
    
    current_price = float(df['Close'].iloc[-1])
    
    # Flag boundaries
    flag_high = float(flag_data['High'].max())
    flag_low = float(flag_data['Low'].min())
    flag_range = flag_high - flag_low
    
    # Flag should be tight consolidation (less than 5% range)
    if flag_range / flag_high > 0.05:
        return None
    
    # Determine flag direction
    if flagpole_end > flagpole_start:  # Bullish flagpole
        # Bullish flag: slight downward or sideways consolidation
        flag_trend = (flag_data['Close'].iloc[-1] - flag_data['Close'].iloc[0]) / flag_data['Close'].iloc[0]
        
        # Should be slight pullback or sideways
        if flag_trend > 0.02:  # Too much upward movement
            return None
        
        # Check for breakout from flag
        breakout_level = flag_high
        near_breakout = current_price >= breakout_level * 0.98
        
        if near_breakout:
            # Bullish flag breakout
            target = current_price + flagpole_change * current_price * 0.6  # 60% of flagpole
            stop_loss = flag_low * 0.98
            
            return {
                "pattern": "Bullish Flag",
                "cmp": current_price,
                "breakout": breakout_level,
                "stop_loss": stop_loss,
                "target": target,
                "volume": True,
                "status": "BREAKOUT" if current_price > breakout_level else "NEAR"
            }
    
    else:  # Bearish flagpole
        # Bearish flag: slight upward or sideways consolidation
        flag_trend = (flag_data['Close'].iloc[-1] - flag_data['Close'].iloc[0]) / flag_data['Close'].iloc[0]
        
        # Should be slight bounce or sideways
        if flag_trend < -0.02:  # Too much downward movement
            return None
        
        # Check for breakdown from flag
        breakdown_level = flag_low
        near_breakdown = current_price <= breakdown_level * 1.02
        
        if near_breakdown:
            # Bearish flag breakdown
            target = current_price - flagpole_change * current_price * 0.6  # 60% of flagpole
            stop_loss = flag_high * 1.02
            
            return {
                "pattern": "Bearish Flag",
                "cmp": current_price,
                "breakout": breakdown_level,
                "stop_loss": stop_loss,
                "target": target,
                "volume": True,
                "status": "BREAKDOWN" if current_price < breakdown_level else "NEAR"
            }
    
    return None

def detect_pennant(df):
    if df is None or len(df) < 40:
        return None
    
    # Pennant: converging trendlines after strong move
    # Similar to flag but with converging boundaries
    
    # Strong move (flagpole)
    flagpole_period = min(15, len(df) - 20)
    flagpole_data = df.tail(flagpole_period)
    
    flagpole_start = float(flagpole_data['Close'].iloc[0])
    flagpole_end = float(flagpole_data['Close'].iloc[-1])
    flagpole_change = abs(flagpole_end - flagpole_start) / flagpole_start
    
    if flagpole_change < 0.10:
        return None
    
    # Pennant: converging consolidation
    pennant_period = min(10, len(df) - flagpole_period)
    pennant_data = df.tail(pennant_period)
    
    current_price = float(df['Close'].iloc[-1])
    
    # Check for converging highs and lows
    highs = pennant_data['High'].values
    lows = pennant_data['Low'].values
    
    # Calculate trendlines
    import numpy as np
    x = np.arange(len(highs))
    
    # High trendline (should be sloping down for bullish pennant)
    high_slope = np.polyfit(x, highs, 1)[0]
    # Low trendline (should be sloping up for bullish pennant)
    low_slope = np.polyfit(x, lows, 1)[0]
    
    # For bullish pennant: high_slope < 0, low_slope > 0
    if high_slope < 0 and low_slope > 0:
        # Bullish pennant
        breakout_level = highs[-1]  # Recent high
        near_breakout = current_price >= breakout_level * 0.98
        
        if near_breakout:
            target = current_price + flagpole_change * current_price * 0.5
            stop_loss = lows[-1] * 0.98
            
            return {
                "pattern": "Bullish Pennant",
                "cmp": current_price,
                "breakout": breakout_level,
                "stop_loss": stop_loss,
                "target": target,
                "volume": True,
                "status": "BREAKOUT" if current_price > breakout_level else "NEAR"
            }
    
    # For bearish pennant: high_slope > 0, low_slope < 0
    elif high_slope > 0 and low_slope < 0:
        # Bearish pennant
        breakdown_level = lows[-1]  # Recent low
        near_breakdown = current_price <= breakdown_level * 1.02
        
        if near_breakdown:
            target = current_price - flagpole_change * current_price * 0.5
            stop_loss = highs[-1] * 1.02
            
            return {
                "pattern": "Bearish Pennant",
                "cmp": current_price,
                "breakout": breakdown_level,
                "stop_loss": stop_loss,
                "target": target,
                "volume": True,
                "status": "BREAKDOWN" if current_price < breakdown_level else "NEAR"
            }
    
    return None
