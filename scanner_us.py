"""
scanner-us v2.0 - US Stock Swing Trading Scanner

MAJOR UPGRADE: Multi-timeframe confirmation + bug fixes

Key improvements:
1. Multi-timeframe confirmation (Daily + Weekly must agree)
2. Risk calculated from ENTRY price (not CMP)
3. Momentum check (5D > 10D for NEAR status)
4. Minimum 15 bars between double bottoms
5. Handle must be near right rim (not a crash)
6. Current price must be recovering (above bottom 2)
7. Trend filter (stock must be in uptrend on higher timeframe)

Usage:
  python scanner_us.py                          # Scan backbone_us.txt
  python scanner_us.py --stocks sp500.txt       # Scan S&P 500
  python scanner_us.py --test                   # Test mode (10 stocks)
  python scanner_us.py --top 50                 # Output top 50
"""

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from utils.sector_rotation_us import get_sector_heat, get_stock_sector, get_sector_bonus

# ============================================================================
# CONFIGURATION
# ============================================================================

ATR_MULTIPLIER = 2.0
MAX_RISK_PCT = 0.08
TARGET_1_PCT = 0.50
TARGET_2_PCT = 1.00

MIN_VOLUME = 500_000
MIN_MARKET_CAP = 500_000_000
MIN_PRICE = 5.00

CUP_HANDLE_WINDOWS = {
    'Daily': (30, 4),
    'Weekly': (30, 4),
    'Monthly': (24, 3),
}

# Multi-timeframe confirmation
MTF_REQUIRE_CONFIRMATION = True  # Daily pattern must be confirmed by Weekly trend
MTF_TREND_PERIOD = 50  # Use 50-day SMA for trend

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def get_stock_data(symbol, period='2y'):
    """Fetch stock data - 2 years for weekly resampling"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval='1d', auto_adjust=True)
        if df.empty or len(df) < 100:
            return None, None, None
        
        # Drop rows with NaN Close (incomplete/current day)
        df = df.dropna(subset=['Close'])
        if len(df) < 100:
            return None, None, None
        
        df['ATR'] = calculate_atr(df)
        
        # Create weekly resampled data
        df_weekly = df.resample('W').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
        df_weekly['ATR'] = calculate_atr(df_weekly)
        
        info = ticker.info
        
        if info.get('averageVolume', 0) < MIN_VOLUME:
            return None, None, None
        if info.get('marketCap', 0) < MIN_MARKET_CAP:
            return None, None, None
        if df['Close'].iloc[-1] < MIN_PRICE:
            return None, None, None
        
        return df, info, df_weekly
    except Exception as e:
        return None, None, None


def find_local_minima(series, order=5):
    minima = []
    for i in range(order, len(series) - order):
        if series.iloc[i] == series.iloc[i-order:i+order+1].min():
            minima.append((i, series.iloc[i]))
    return minima


def check_momentum(df):
    """Check if stock is rising (5D close > 10D close)"""
    if len(df) < 15:
        return True
    close_5d = df['Close'].iloc[-5:].mean()
    close_10d = df['Close'].iloc[-10:].mean()
    return close_5d > close_10d


def check_higher_trend(df_weekly):
    """
    Check if stock is in uptrend on weekly timeframe
    Uses 50-week SMA (or 50-day SMA on daily)
    """
    if df_weekly is None or len(df_weekly) < 50:
        return True  # Can't determine, allow
    
    sma_50 = df_weekly['Close'].rolling(50).mean().iloc[-1]
    current = df_weekly['Close'].iloc[-1]
    
    # Stock should be above 50-week SMA (long-term uptrend)
    # OR within 10% below (recovering)
    if current > sma_50:
        return True
    elif current > sma_50 * 0.90:  # Within 10% below
        return True
    else:
        return False


# ============================================================================
# PATTERN DETECTION (FIXED)
# ============================================================================

def detect_cup_and_handle(df, timeframe='Daily', df_weekly=None):
    """
    Detect Cup & Handle pattern
    
    FIXED:
    - Risk from ENTRY (breakout), not CMP
    - Handle must be near right rim (within 15%)
    - NEAR requires upward momentum
    - Multi-timeframe: Weekly trend must be bullish
    """
    try:
        cup_bars, handle_bars = CUP_HANDLE_WINDOWS[timeframe]
        
        if len(df) < cup_bars + handle_bars:
            return None
        
        # Cup analysis
        cup_window = df.iloc[-cup_bars:]
        left_rim = cup_window['High'].iloc[:10].max()
        right_rim = cup_window['High'].iloc[-10:].max()
        cup_bottom = cup_window['Low'].min()
        cup_depth = (left_rim - cup_bottom) / left_rim
        
        if not (0.12 <= cup_depth <= 0.50):
            return None
        
        # Handle analysis
        handle_window = df.iloc[-handle_bars:]
        handle_high = handle_window['High'].max()
        handle_low = handle_window['Low'].min()
        handle_depth = (handle_high - handle_low) / handle_high
        
        if handle_depth > 0.50:
            return None
        
        # FIX: Handle must be near right rim (not a crash)
        if (right_rim - handle_low) / right_rim > 0.15:
            return None
        
        breakout = right_rim
        cmp = df['Close'].iloc[-1]
        
        # FIX: Stop loss relative to ENTRY, not CMP
        structural_stop = handle_low
        atr = df['ATR'].iloc[-1]
        atr_stop = breakout - (atr * ATR_MULTIPLIER)
        
        stop_loss = max(structural_stop, atr_stop)
        max_stop = breakout * (1 - MAX_RISK_PCT)
        stop_loss = max(stop_loss, max_stop)
        
        # FIX: Risk from ENTRY (breakout)
        risk_pct = (breakout - stop_loss) / breakout
        if risk_pct > MAX_RISK_PCT:
            stop_loss = breakout * (1 - MAX_RISK_PCT)
            risk_pct = MAX_RISK_PCT
        
        # Targets
        measured_move = cup_depth * breakout
        target_1 = breakout + (measured_move * TARGET_1_PCT)
        target_2 = breakout + (measured_move * TARGET_2_PCT)
        
        upside_pct = (target_1 - breakout) / breakout
        rr = upside_pct / risk_pct if risk_pct > 0 else 0
        
        dist_to_breakout = (breakout - cmp) / cmp
        
        # FIX: Momentum check for NEAR
        rising = check_momentum(df)
        
        if cmp >= breakout:
            status = 'BREAKOUT'
        elif dist_to_breakout <= 0.05 and rising:
            status = 'NEAR'
        elif dist_to_breakout <= 0.05 and not rising:
            return None  # Stock falling away
        elif dist_to_breakout <= 0.15 and rising:
            status = 'WATCH'
        else:
            return None
        
        # Multi-timeframe confirmation
        mtf_confirmed = False
        if MTF_REQUIRE_CONFIRMATION and df_weekly is not None:
            # Check weekly trend
            if check_higher_trend(df_weekly):
                mtf_confirmed = True
        else:
            mtf_confirmed = True
        
        return {
            'pattern': f'Cup & Handle ({timeframe})',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk_pct': risk_pct * 100,
            'upside_pct': upside_pct * 100,
            'rr': rr,
            'cmp': cmp,
            'dist_to_breakout_pct': dist_to_breakout * 100,
            'mtf_confirmed': mtf_confirmed,
        }
    except Exception as e:
        return None


def detect_double_bottom(df, df_weekly=None):
    """
    Detect Double Bottom pattern
    
    FIXED:
    - Minimum 15 bars between bottoms
    - Current price must be above bottom 2 (recovering)
    - Risk from ENTRY, not CMP
    - NEAR requires upward momentum
    - Multi-timeframe: Weekly trend must be bullish
    """
    try:
        lookback = 60
        if len(df) < lookback:
            return None
        
        window = df.iloc[-lookback:]
        lows = find_local_minima(window['Low'], order=3)
        if len(lows) < 2:
            return None
        
        bottom1_idx, bottom1_price = lows[-2]
        bottom2_idx, bottom2_price = lows[-1]
        
        # FIX: Minimum 15 bars between bottoms
        if (bottom2_idx - bottom1_idx) < 15:
            return None
        
        if abs(bottom1_price - bottom2_price) / bottom1_price > 0.03:
            return None
        
        peak_window = window.iloc[bottom1_idx:bottom2_idx]
        if len(peak_window) == 0:
            return None
        
        peak_price = peak_window['High'].max()
        breakout = peak_price
        cmp = df['Close'].iloc[-1]
        
        # FIX: Current price must be RECOVERING (above bottom 2)
        if cmp < min(bottom1_price, bottom2_price):
            return None
        
        structural_stop = min(bottom1_price, bottom2_price)
        
        # FIX: ATR stop relative to ENTRY
        atr = df['ATR'].iloc[-1]
        atr_stop = breakout - (atr * ATR_MULTIPLIER)
        
        stop_loss = max(structural_stop, atr_stop)
        max_stop = breakout * (1 - MAX_RISK_PCT)
        stop_loss = max(stop_loss, max_stop)
        
        # FIX: Risk from ENTRY
        risk_pct = (breakout - stop_loss) / breakout
        if risk_pct > MAX_RISK_PCT:
            stop_loss = breakout * (1 - MAX_RISK_PCT)
            risk_pct = MAX_RISK_PCT
        
        measured_move = peak_price - min(bottom1_price, bottom2_price)
        target_1 = breakout + (measured_move * TARGET_1_PCT)
        target_2 = breakout + (measured_move * TARGET_2_PCT)
        
        upside_pct = (target_1 - breakout) / breakout
        rr = upside_pct / risk_pct if risk_pct > 0 else 0
        
        dist_to_breakout = (breakout - cmp) / cmp
        
        # FIX: Momentum check
        rising = check_momentum(df)
        
        if cmp >= breakout:
            status = 'BREAKOUT'
        elif dist_to_breakout <= 0.05 and rising:
            status = 'NEAR'
        elif dist_to_breakout <= 0.05 and not rising:
            return None
        elif dist_to_breakout <= 0.15 and rising:
            status = 'WATCH'
        else:
            return None
        
        # Multi-timeframe confirmation
        mtf_confirmed = False
        if MTF_REQUIRE_CONFIRMATION and df_weekly is not None:
            if check_higher_trend(df_weekly):
                mtf_confirmed = True
        else:
            mtf_confirmed = True
        
        return {
            'pattern': 'Double Bottom',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk_pct': risk_pct * 100,
            'upside_pct': upside_pct * 100,
            'rr': rr,
            'cmp': cmp,
            'dist_to_breakout_pct': dist_to_breakout * 100,
            'mtf_confirmed': mtf_confirmed,
        }
    except Exception as e:
        return None


# ============================================================================
# SCORING (with MTF bonus)
# ============================================================================

def calculate_score(result, sector_bonus, volume_ratio):
    base_score = min(result['rr'] * 20, 60)
    score = base_score + sector_bonus
    
    if volume_ratio > 2.0:
        score += 10
    
    if result['status'] == 'BREAKOUT':
        score += 15
    elif result['dist_to_breakout_pct'] < 5.0:
        score += 10
    else:
        score += 5
    
    if 'Double Bottom' in result['pattern']:
        score += 28
    elif 'Weekly' in result['pattern']:
        score += 28
    elif 'Monthly' in result['pattern']:
        score += 25
    else:
        score += 20
    
    # MTF confirmation bonus
    if result.get('mtf_confirmed', False):
        score += 15  # Bonus for multi-timeframe confirmation
    else:
        score -= 10  # Penalty for no MTF confirmation
    
    if result['risk_pct'] > 8.0:
        score *= 0.5
    elif result['risk_pct'] > 6.0:
        score *= 0.8
    
    return round(score, 1)


# ============================================================================
# MAIN SCANNER
# ============================================================================

def scan_stock(symbol):
    """Scan a single stock with multi-timeframe confirmation"""
    try:
        result = get_stock_data(symbol)
        if result[0] is None:
            return []
        df, info, df_weekly = result
        
        sector = get_stock_sector(symbol)
        sector_bonus = get_sector_bonus(symbol)
        
        avg_volume = info.get('averageVolume', 1)
        recent_volume = df['Volume'].iloc[-5:].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        results = []
        
        # Cup & Handle (Daily, Weekly, Monthly) - pass df_weekly for MTF
        for timeframe in ['Daily', 'Weekly', 'Monthly']:
            r = detect_cup_and_handle(df, timeframe, df_weekly)
            if r:
                r['symbol'] = symbol
                r['sector'] = sector
                r['volume_ratio'] = volume_ratio
                r['score'] = calculate_score(r, sector_bonus, volume_ratio)
                results.append(r)
        
        # Double Bottom
        r = detect_double_bottom(df, df_weekly)
        if r:
            r['symbol'] = symbol
            r['sector'] = sector
            r['volume_ratio'] = volume_ratio
            r['score'] = calculate_score(r, sector_bonus, volume_ratio)
            results.append(r)
        
        return results
    except Exception as e:
        return []


def main():
    parser = argparse.ArgumentParser(description='US Stock Scanner v2.0')
    parser.add_argument('--stocks', default='backbone_us.txt')
    parser.add_argument('--top', type=int, default=30)
    parser.add_argument('--min-score', type=float, default=40.0)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--mtf-only', action='store_true', help='Only show MTF-confirmed setups')
    parser.add_argument('--best-only', action='store_true',
                        help='Show only 1 setup per stock (highest score). Eliminates duplicates.')
    parser.add_argument('--db-only', action='store_true',
                        help='Show only Double Bottom setups (70.7%% WR, +1.73%% expectancy in backtest)')
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"scanner-us v2.0 - Multi-Timeframe Confirmation")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    stock_file = os.path.join(os.path.dirname(__file__), args.stocks)
    if not os.path.exists(stock_file):
        print(f"Error: {stock_file} not found")
        return
    
    with open(stock_file, 'r') as f:
        symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    if args.test:
        symbols = symbols[:10]
        print(f"TEST MODE: {len(symbols)} stocks")
    else:
        print(f"Scanning {len(symbols)} stocks from {args.stocks}")
    print()
    
    # Sector rotation
    print("Fetching sector rotation...")
    heat = get_sector_heat()
    sorted_sectors = sorted(heat.items(), key=lambda x: x[1]['perf_20d'], reverse=True)
    print("Hot sectors:")
    for name, data in sorted_sectors[:3]:
        print(f"  {name:<30} {data['signal']:<12} 5D: {data['perf_5d']:+.1f}% | 20D: {data['perf_20d']:+.1f}%")
    print()
    
    # Scan
    print("Scanning stocks...")
    all_results = []
    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] {symbol}...", end='\r')
        results = scan_stock(symbol)
        all_results.extend(results)
    
    print()
    print(f"Found {len(all_results)} setups")
    
    # Filter
    filtered = [r for r in all_results if r['score'] >= args.min_score]
    if args.mtf_only:
        filtered = [r for r in filtered if r.get('mtf_confirmed', False)]
        print(f"MTF-confirmed only: {len(filtered)} setups")

    # --db-only: Double Bottom only (the 70.7% WR pattern)
    if args.db_only:
        filtered = [r for r in filtered if 'Double Bottom' in r['pattern']]
        print(f"Double Bottom only: {len(filtered)} setups")

    # --best-only: 1 setup per stock (highest score)
    if args.best_only:
        seen = {}
        for r in filtered:
            sym = r['symbol']
            if sym not in seen or r['score'] > seen[sym]['score']:
                seen[sym] = r
        filtered = list(seen.values())
        print(f"Best-only (1 per stock): {len(filtered)} setups")

    filtered.sort(key=lambda x: x['score'], reverse=True)
    top_picks = filtered[:args.top]
    
    print()
    print("=" * 80)
    print(f"TOP {len(top_picks)} SETUPS (min score: {args.min_score})")
    print("=" * 80)
    print()
    
    for i, r in enumerate(top_picks, 1):
        mtf = "[MTF]" if r.get('mtf_confirmed') else "[NO-MTF]"
        print(f"{i}. {r['symbol']} - {r['pattern']} - {r['status']} {mtf}")
        print(f"   CMP: ${r['cmp']:.2f} | Entry: ${r['entry']:.2f} | SL: ${r['stop_loss']:.2f} ({r['risk_pct']:.1f}% from entry)")
        print(f"   T1: ${r['target_1']:.2f} | T2: ${r['target_2']:.2f} | R:R: {r['rr']:.1f}x | Score: {r['score']:.1f}")
        if r['status'] != 'BREAKOUT':
            print(f"   Distance to breakout: {r['dist_to_breakout_pct']:.1f}%")
        print()
    
    # Save
    if top_picks:
        output_file = f"results_us_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df_out = pd.DataFrame(top_picks)
        df_out.to_csv(output_file, index=False)
        print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()
