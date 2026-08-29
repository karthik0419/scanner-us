"""
US Sector Rotation Engine
Tracks S&P sector ETF momentum to identify BOOM/RISING/COOLING/WEAK sectors
Based on scanner-v3 sector_rotation_v3.py, adapted for US markets
"""

import yfinance as yf
import pandas as pd
import json
import os

# S&P Sector ETFs (SPDR Select Sector ETFs - most liquid)
SECTOR_ETFS = {
    'Energy': 'XLE',
    'Materials': 'XLB',
    'Industrials': 'XLI',
    'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP',
    'Health Care': 'XLV',
    'Financials': 'XLF',
    'Information Technology': 'XLK',
    'Communication Services': 'XLC',
    'Utilities': 'XLU',
    'Real Estate': 'XLRE',
}

# Cache for session (avoid re-downloading every scan)
_cache = {}


def get_sector_heat(lookback_short=5, lookback_long=20):
    """
    Returns dict: sector -> {'perf_5d', 'perf_20d', 'signal', 'bonus'}
    signal: BOOM / RISING / COOLING / WEAK
    bonus: +20 BOOM, +10 RISING, 0 COOLING, -10 WEAK
    Cached for the session.
    """
    global _cache
    if _cache:
        return _cache

    heat = {}
    for sector, etf in SECTOR_ETFS.items():
        try:
            df = yf.download(etf, period='3mo', interval='1d',
                             progress=False, auto_adjust=True)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) < lookback_long + 2:
                continue

            curr   = float(df['Close'].iloc[-1])
            p5     = float(df['Close'].iloc[-(lookback_short+1)])
            p20    = float(df['Close'].iloc[-(lookback_long+1)])

            perf_5d  = round((curr - p5)  / p5  * 100, 2)
            perf_20d = round((curr - p20) / p20 * 100, 2)

            if perf_5d > 2 and perf_20d > 3:
                signal, bonus = 'BOOM',    20
            elif perf_5d > 0 and perf_20d > 0:
                signal, bonus = 'RISING',  10
            elif perf_5d < 0 and perf_20d > 0:
                signal, bonus = 'COOLING',  0
            else:
                signal, bonus = 'WEAK',   -10

            heat[sector] = {
                'perf_5d':  perf_5d,
                'perf_20d': perf_20d,
                'signal':   signal,
                'bonus':    bonus,
            }
        except Exception as e:
            print(f"Warning: Could not fetch {etf} ({sector}): {e}")
            pass

    _cache = heat
    return heat


def get_stock_sector(symbol):
    """
    Return sector name for a given stock symbol.
    
    Lookup priority:
      1. S&P 500 official GICS sector map (sp500_sectors.json)
      2. yfinance 'sector' field
      3. 'Unknown'
    """
    # Layer 1: S&P 500 official mapping
    sp500_path = os.path.join(os.path.dirname(__file__), '..', 'sp500_sectors.json')
    if os.path.exists(sp500_path):
        with open(sp500_path, 'r') as f:
            sp500_sectors = json.load(f)
            if symbol in sp500_sectors:
                return sp500_sectors[symbol]
    
    # Layer 2: yfinance metadata
    try:
        ticker = yf.Ticker(symbol)
        sector = ticker.info.get('sector', None)
        if sector:
            # Map yfinance sector names to GICS sectors
            # yfinance uses slightly different names
            sector_map = {
                'Technology': 'Information Technology',
                'Healthcare': 'Health Care',
                'Financial Services': 'Financials',
                'Consumer Cyclical': 'Consumer Discretionary',
                'Consumer Defensive': 'Consumer Staples',
                'Basic Materials': 'Materials',
                'Communication Services': 'Communication Services',
                'Energy': 'Energy',
                'Industrials': 'Industrials',
                'Real Estate': 'Real Estate',
                'Utilities': 'Utilities',
            }
            return sector_map.get(sector, sector)
    except:
        pass
    
    return 'Unknown'


def get_sector_bonus(symbol):
    """
    Return score bonus for a stock based on its sector momentum.
    +20 BOOM, +10 RISING, 0 COOLING, -10 WEAK
    """
    sector = get_stock_sector(symbol)
    heat = get_sector_heat()
    
    if sector in heat:
        return heat[sector]['bonus']
    return 0


def get_weak_sectors():
    """Return list of WEAK sectors (20D negative)"""
    heat = get_sector_heat()
    return [name for name, data in heat.items() if data['signal'] == 'WEAK']


def get_hot_sectors(top_n=3):
    """
    Return top N BOOM/RISING sectors by 20D performance.
    Filters out COOLING/WEAK sectors.
    """
    heat = get_sector_heat()
    boom_rising = [(name, data['perf_5d'], data['perf_20d']) 
                   for name, data in heat.items() 
                   if data['signal'] in ['BOOM', 'RISING']]
    
    # Sort by 20D performance descending
    boom_rising.sort(key=lambda x: x[2], reverse=True)
    return boom_rising[:top_n]


def print_sector_heatmap():
    """Print sector rotation heatmap (for debugging/analysis)"""
    heat = get_sector_heat()
    sorted_sectors = sorted(heat.items(), key=lambda x: x[1]['perf_20d'], reverse=True)
    
    print("=" * 80)
    print("US SECTOR ROTATION HEAT MAP")
    print("=" * 80)
    print(f"{'Rank':<6} {'Sector':<30} {'Signal':<12} {'5D%':<8} {'20D%':<8}")
    print("-" * 80)
    
    for i, (name, data) in enumerate(sorted_sectors, 1):
        signal = data['signal']
        perf_5d = data['perf_5d']
        perf_20d = data['perf_20d']
        
        print(f"{i:<6} {name:<30} {signal:<12} {perf_5d:>6.1f}% {perf_20d:>6.1f}%")
    
    print("=" * 80)


if __name__ == '__main__':
    # Test the module
    print_sector_heatmap()
    print()
    print("Hot sectors:", get_hot_sectors(3))
    print("Weak sectors:", get_weak_sectors())
    print()
    print("Test sector lookup:")
    print(f"  AAPL -> {get_stock_sector('AAPL')} (bonus: {get_sector_bonus('AAPL')})")
    print(f"  JPM -> {get_stock_sector('JPM')} (bonus: {get_sector_bonus('JPM')})")
    print(f"  XOM -> {get_stock_sector('XOM')} (bonus: {get_sector_bonus('XOM')})")
