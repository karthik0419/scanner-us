def detect_darvas_box(df):
    if df is None or len(df) < 50:
        return None
    
    # Darvas Box looks for consolidation followed by breakout
    # Need at least 20-30 days of box formation
    
    box_period = min(30, len(df) - 10)
    box_data = df.tail(box_period)
    
    current_price = float(df['Close'].iloc[-1])
    
    # Find box boundaries
    box_high = float(box_data['High'].max())
    box_low = float(box_data['Low'].min())
    box_range = box_high - box_low
    
    # Box should have reasonable range (8-15% for better patterns)
    if box_range / box_high < 0.08 or box_range / box_high > 0.15:
        return None
    
    # Check for multiple touches of box boundaries
    high_touches = 0
    low_touches = 0
    
    for _, row in box_data.iterrows():
        if abs(row['High'] - box_high) / box_high < 0.02:
            high_touches += 1
        if abs(row['Low'] - box_low) / box_low < 0.02:
            low_touches += 1
    
    # Need at least 2 touches each
    if high_touches < 2 or low_touches < 2:
        return None
    
    # Check if price is breaking out of box
    breakout_level = box_high
    breakdown_level = box_low
    
    breakout = current_price >= breakout_level * 1.01
    breakdown = current_price <= breakdown_level * 0.99
    near_breakout = current_price >= breakout_level * 0.98
    near_breakdown = current_price <= breakdown_level * 1.02
    
    # Volume confirmation
    avg_volume = float(df['Volume'].tail(20).mean())
    current_volume = float(df['Volume'].iloc[-1])
    volume_spike = current_volume > avg_volume * 1.5
    
    if breakout:
        # Long setup
        target = box_high + box_range * 0.5
        stop_loss = box_low * 0.98
        
        return {
            "pattern": "Darvas Box",
            "cmp": current_price,
            "breakout": breakout_level,
            "stop_loss": stop_loss,
            "target": target,
            "volume": volume_spike,
            "status": "BREAKOUT"
        }
    
    elif breakdown:
        # Short setup
        target = box_low - box_range * 0.5
        stop_loss = box_high * 1.02
        
        return {
            "pattern": "Darvas Box",
            "cmp": current_price,
            "breakout": breakdown_level,
            "stop_loss": stop_loss,
            "target": target,
            "volume": volume_spike,
            "status": "BREAKDOWN"
        }
    
    elif near_breakout:
        # Near breakout setup
        target = box_high + box_range * 0.5
        stop_loss = box_low * 0.98
        
        return {
            "pattern": "Darvas Box",
            "cmp": current_price,
            "breakout": breakout_level,
            "stop_loss": stop_loss,
            "target": target,
            "volume": False,
            "status": "NEAR"
        }
    
    return None
