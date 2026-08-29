"""
backtest_us_v2.py - Backtest with rate limiting handling

Improvements over v1:
1. Sleep delays between yfinance requests (avoid rate limiting)
2. Retry logic with exponential backoff
3. Data caching (avoid re-downloading same stock)
4. Bi-weekly scans (reduce requests by 50%)
5. Progress tracking (see estimated time remaining)

Usage:
  python backtest_us_v2.py --stocks backbone_us.txt --years 5
"""

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
import time
import pickle
import os
from datetime import datetime, timedelta
from scanner_us import get_sector_heat
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

SLEEP_BETWEEN_REQUESTS = 0.5  # 0.5 seconds between yfinance calls
MAX_RETRIES = 3
RETRY_DELAY = 5  # Start with 5 second delay on retry
CACHE_DIR = "backtest_cache"

# ============================================================================
# DATA FETCHER WITH RATE LIMITING
# ============================================================================

def fetch_with_retry(symbol, start_date, end_date, cache={}):
    """
    Fetch stock data with retry logic and caching
    """
    # Check cache first
    cache_key = f"{symbol}_{start_date}_{end_date}"
    if cache_key in cache:
        return cache[cache_key]
    
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(SLEEP_BETWEEN_REQUESTS)  # Rate limiting
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, auto_adjust=True)
            
            if df is not None and not df.empty:
                cache[cache_key] = df
                return df
            
            return None
        
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate" in str(e):
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                print(f"  Rate limited on {symbol}, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None
    
    return None


def calculate_atr(df, period=14):
    """Calculate ATR"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def scan_stock_historical(symbol, scan_date, data_cache):
    """
    Scan a stock on a specific historical date
    Uses pre-downloaded data to avoid re-fetching
    """
    try:
        # Get data up to scan date
        start = scan_date - timedelta(days=400)  # Need ~1 year of data
        df = fetch_with_retry(symbol, start, scan_date, cache=data_cache)
        
        if df is None or df.empty or len(df) < 100:
            return []
        
        # Calculate ATR
        df['ATR'] = calculate_atr(df)
        
        # Detect patterns (simplified - just Cup & Handle Daily for speed)
        results = []
        
        # Cup & Handle detection (simplified)
        cup_bars = 30
        handle_bars = 4
        
        if len(df) < cup_bars + handle_bars:
            return []
        
        cup_window = df.iloc[-cup_bars:]
        left_rim = cup_window['High'].iloc[:10].max()
        right_rim = cup_window['High'].iloc[-10:].max()
        cup_bottom = cup_window['Low'].min()
        cup_depth = (left_rim - cup_bottom) / left_rim
        
        if not (0.12 <= cup_depth <= 0.50):
            return []
        
        handle_window = df.iloc[-handle_bars:]
        handle_high = handle_window['High'].max()
        handle_low = handle_window['Low'].min()
        handle_depth = (handle_high - handle_low) / handle_high
        
        if handle_depth > 0.50:
            return []
        
        # Breakout level
        breakout = right_rim
        cmp = df['Close'].iloc[-1]
        
        # Stop loss (2.0x ATR, capped at 8%)
        atr = df['ATR'].iloc[-1]
        atr_stop = cmp - (atr * 2.0)
        structural_stop = handle_low
        stop_loss = max(structural_stop, atr_stop)
        stop_loss = max(stop_loss, cmp * 0.92)
        
        risk_pct = (cmp - stop_loss) / cmp
        if risk_pct > 0.08:
            return []
        
        # Targets
        measured_move = cup_depth * breakout
        target_1 = breakout + (measured_move * 0.50)
        target_2 = breakout + (measured_move * 1.00)
        
        # Status
        dist = (breakout - cmp) / cmp
        if cmp >= breakout:
            status = 'BREAKOUT'
        elif dist <= 0.05:
            status = 'NEAR'
        else:
            return []
        
        # R:R
        upside = (target_1 - breakout) / breakout
        rr = upside / risk_pct if risk_pct > 0 else 0
        
        if rr < 1.5:  # Min R:R filter
            return []
        
        results.append({
            'symbol': symbol,
            'pattern': 'Cup & Handle (Daily)',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'scan_date': scan_date,
        })
        
        return results
    
    except Exception as e:
        return []


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class Trade:
    def __init__(self, symbol, pattern, entry_date, entry_price, stop_loss, target_1, target_2):
        self.symbol = symbol
        self.pattern = pattern
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target_1 = target_1
        self.target_2 = target_2
        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_pct = 0.0
        self.days_held = 0
        self.status = 'OPEN'
    
    def close(self, exit_date, exit_price, reason):
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        self.days_held = (exit_date - self.entry_date).days
        self.status = 'CLOSED'


def run_backtest(symbols, years=5, capital=10000):
    """Run backtest with rate limiting"""
    
    print("=" * 80)
    print("BACKTEST v2 - scanner-us (with rate limiting)")
    print("=" * 80)
    print(f"Stocks: {len(symbols)}")
    print(f"Period: {years} years")
    print(f"Starting capital: ${capital:,.0f}")
    print(f"Sleep between requests: {SLEEP_BETWEEN_REQUESTS}s")
    print("=" * 80)
    print()
    
    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    # Generate scan dates (bi-weekly to reduce requests)
    scan_dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() == 0:  # Monday
            scan_dates.append(current)
            current += timedelta(days=14)  # Skip 1 week (bi-weekly)
        else:
            current += timedelta(days=1)
    
    print(f"Scan dates: {len(scan_dates)} (bi-weekly scans)")
    print(f"Estimated time: {len(scan_dates) * len(symbols) * SLEEP_BETWEEN_REQUESTS / 60:.1f} minutes")
    print()
    
    # Data cache (shared across all scans)
    data_cache = {}
    
    # Backtest state
    open_trades = []
    closed_trades = []
    
    start_time = time.time()
    
    # Run backtest
    for scan_idx, scan_date in enumerate(scan_dates):
        elapsed = time.time() - start_time
        progress = (scan_idx + 1) / len(scan_dates) * 100
        eta = (elapsed / (scan_idx + 1)) * (len(scan_dates) - scan_idx - 1) if scan_idx > 0 else 0
        
        print(f"[{scan_idx+1}/{len(scan_dates)}] {scan_date.strftime('%Y-%m-%d')} | {progress:.1f}% | ETA {eta/60:.1f}m | Open: {len(open_trades)} | Closed: {len(closed_trades)}")
        
        # Close open trades first
        for trade in list(open_trades):
            try:
                # Fetch data from entry to now
                df = fetch_with_retry(trade.symbol, trade.entry_date, scan_date + timedelta(days=1), cache=data_cache)
                
                if df is None or df.empty:
                    continue
                
                # Check stop loss
                if df['Low'].min() <= trade.stop_loss:
                    idx = df[df['Low'] <= trade.stop_loss].index[0]
                    trade.close(idx, trade.stop_loss, 'LOSS')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
                
                # Check target 1
                if df['High'].max() >= trade.target_1:
                    idx = df[df['High'] >= trade.target_1].index[0]
                    trade.close(idx, trade.target_1, 'WIN_T1')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
                
                # Check time exit (45 days)
                if (scan_date - trade.entry_date).days >= 45:
                    exit_price = df['Close'].iloc[-1]
                    trade.close(scan_date, exit_price, 'TIME_EXIT')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
            
            except Exception as e:
                pass
        
        # Scan for new setups
        for symbol in symbols:
            try:
                # Skip if already have open trade
                if any(t.symbol == symbol for t in open_trades):
                    continue
                
                # Scan
                results = scan_stock_historical(symbol, scan_date, data_cache)
                if not results:
                    continue
                
                # Take first BREAKOUT
                best = [r for r in results if r['status'] == 'BREAKOUT']
                if not best:
                    continue
                
                setup = best[0]
                
                # Enter next day
                df = fetch_with_retry(symbol, scan_date, scan_date + timedelta(days=5), cache=data_cache)
                if df is None or df.empty:
                    continue
                
                entry_date = df.index[0]
                entry_price = df['Open'].iloc[0]
                
                trade = Trade(
                    symbol=symbol,
                    pattern=setup['pattern'],
                    entry_date=entry_date,
                    entry_price=entry_price,
                    stop_loss=setup['stop_loss'],
                    target_1=setup['target_1'],
                    target_2=setup['target_2'],
                )
                open_trades.append(trade)
            
            except Exception as e:
                pass
    
    print()
    print(f"Backtest complete. Elapsed: {(time.time() - start_time)/60:.1f} minutes")
    print()
    
    # Close remaining trades
    for trade in open_trades:
        try:
            df = fetch_with_retry(trade.symbol, trade.entry_date, end_date, cache=data_cache)
            if df is not None and not df.empty:
                exit_price = df['Close'].iloc[-1]
                trade.close(end_date, exit_price, 'BACKTEST_END')
                closed_trades.append(trade)
        except:
            pass
    
    # Calculate stats
    total_trades = len(closed_trades)
    if total_trades == 0:
        print("No trades found.")
        return
    
    wins = [t for t in closed_trades if t.pnl_pct > 0]
    losses = [t for t in closed_trades if t.pnl_pct <= 0]
    
    win_rate = len(wins) / total_trades * 100
    avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
    expectancy = np.mean([t.pnl_pct for t in closed_trades])
    
    total_gains = sum(t.pnl_pct for t in wins) if wins else 0
    total_losses = abs(sum(t.pnl_pct for t in losses)) if losses else 1
    profit_factor = total_gains / total_losses if total_losses > 0 else 0
    
    # Print results
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print()
    print(f"Total trades: {total_trades}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg win: {avg_win:+.1f}%")
    print(f"Avg loss: {avg_loss:+.1f}%")
    print(f"Expectancy: {expectancy:+.2f}% per trade")
    print(f"Profit factor: {profit_factor:.2f}")
    print()
    
    # Sample trades
    print("Last 20 trades:")
    for trade in closed_trades[-20:]:
        print(f"  {trade.symbol:6} {trade.entry_date.strftime('%Y-%m-%d')} → {trade.exit_date.strftime('%Y-%m-%d')} | {trade.exit_reason:12} | {trade.pnl_pct:+6.1f}% ({trade.days_held}d)")
    print()
    
    # Save
    df = pd.DataFrame([{
        'symbol': t.symbol,
        'entry_date': t.entry_date,
        'exit_date': t.exit_date,
        'entry_price': t.entry_price,
        'exit_price': t.exit_price,
        'pnl_pct': t.pnl_pct,
        'exit_reason': t.exit_reason,
        'days_held': t.days_held,
    } for t in closed_trades])
    
    output = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output, index=False)
    print(f"Saved to: {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stocks', default='backbone_us.txt')
    parser.add_argument('--years', type=int, default=5)
    parser.add_argument('--capital', type=float, default=10000)
    args = parser.parse_args()
    
    with open(args.stocks, 'r') as f:
        symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    run_backtest(symbols, years=args.years, capital=args.capital)


if __name__ == '__main__':
    main()
