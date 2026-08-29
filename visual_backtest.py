"""
visual_backtest.py - Visual backtest with cached data

Approach:
1. Download ALL data ONCE per stock (cache to disk)
2. Replay day-by-day from cached data (no yfinance calls)
3. Detect patterns at each historical date
4. Simulate trades (entry, SL, T1, T2, time exit)
5. Show visual chart of equity curve + trade markers

No rate limiting because data is fetched once and cached.

Usage:
  python visual_backtest.py --stocks backbone_us.txt --years 2
  python visual_backtest.py --stocks backbone_us.txt --years 5 --visual
  python visual_backtest.py --test  # 10 stocks, 1 year
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
import pickle
import time
from datetime import datetime, timedelta
from scanner_us import (
    calculate_atr, find_local_minima, check_momentum, check_higher_trend,
    CUP_HANDLE_WINDOWS, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT
)
from patterns import (
    detect_bull_flag, detect_pennant,
    detect_ascending_triangle, detect_symmetrical_triangle,
    detect_falling_wedge, detect_channel_breakout, detect_rectangle,
    detect_double_top, detect_inverse_head_shoulders,
)
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = "backtest_cache"
SCAN_INTERVAL = 14  # Scan every 14 days (bi-weekly)
MAX_HOLD_DAYS = 45
SLEEP_BETWEEN_DOWNLOADS = 0.3  # Only during initial download

plt.style.use('dark_background')


# ============================================================================
# DATA CACHE - Download once, use forever
# ============================================================================

def download_and_cache(symbols, years, refresh=False):
    """Download all stock data once and cache to disk.

    Args:
        symbols: List of stock symbols to download
        years: Number of years of history
        refresh: If True, merge new stocks into existing cache (incremental).
                 Only downloads stocks NOT already in cache.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = os.path.join(CACHE_DIR, f"all_stocks_{years}y.pkl")

    # --- Incremental refresh mode ---
    if refresh and os.path.exists(cache_file):
        print(f"Loading existing cache to find new stocks...")
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)

        # Find stocks that are in sp500.txt but NOT in cache
        new_symbols = [s for s in symbols if s not in cached_data]
        already_cached = [s for s in symbols if s in cached_data]

        print(f"  Already cached: {len(already_cached)} stocks")
        print(f"  New stocks to download: {len(new_symbols)}")

        if not new_symbols:
            print(f"  Cache is up to date — no new stocks to download.")
            return cached_data

        print(f"\nDownloading {len(new_symbols)} NEW stocks ({years} years)...")
        print(f"This takes ~{len(new_symbols) * SLEEP_BETWEEN_DOWNLOADS / 60:.1f} minutes")
        print()

        start_date = datetime.now() - timedelta(days=years * 365 + 100)

        for i, symbol in enumerate(new_symbols, 1):
            print(f"  [{i}/{len(new_symbols)}] {symbol}...", end='\r')
            try:
                time.sleep(SLEEP_BETWEEN_DOWNLOADS)
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, auto_adjust=True)

                if df is not None and not df.empty and len(df) > 100:
                    df = df.dropna(subset=['Close'])
                    df['ATR'] = calculate_atr(df)
                    df_weekly = df.resample('W').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min',
                        'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    df_weekly['ATR'] = calculate_atr(df_weekly)
                    df_monthly = df.resample('ME').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min',
                        'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    df_monthly['ATR'] = calculate_atr(df_monthly)
                    cached_data[symbol] = {'daily': df, 'weekly': df_weekly, 'monthly': df_monthly}
            except Exception:
                pass

        print()
        new_count = len([s for s in new_symbols if s in cached_data])
        print(f"Downloaded {new_count}/{len(new_symbols)} new stocks successfully")

        # Save merged cache
        with open(cache_file, 'wb') as f:
            pickle.dump(cached_data, f)
        print(f"Cache updated: {cache_file} ({len(cached_data)} total stocks)")
        print()

        return cached_data

    # --- Normal mode (fresh download or use existing cache) ---
    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        age = (datetime.now() - mtime).total_seconds() / 3600
        if age < 24:
            print(f"Loading cached data ({age:.1f}h old)...")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

    print(f"Downloading {len(symbols)} stocks ({years} years) - ONE TIME ONLY...")
    print(f"This takes ~{len(symbols) * SLEEP_BETWEEN_DOWNLOADS / 60:.1f} minutes")
    print()

    all_data = {}
    start_date = datetime.now() - timedelta(days=years * 365 + 100)

    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] {symbol}...", end='\r')

        try:
            time.sleep(SLEEP_BETWEEN_DOWNLOADS)
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, auto_adjust=True)

            if df is not None and not df.empty and len(df) > 100:
                df = df.dropna(subset=['Close'])
                df['ATR'] = calculate_atr(df)
                # Create weekly resampled
                df_weekly = df.resample('W').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum'
                }).dropna()
                df_weekly['ATR'] = calculate_atr(df_weekly)
                # Create monthly resampled
                df_monthly = df.resample('ME').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum'
                }).dropna()
                df_monthly['ATR'] = calculate_atr(df_monthly)

                all_data[symbol] = {'daily': df, 'weekly': df_weekly, 'monthly': df_monthly}
        except Exception as e:
            pass

    print()
    print(f"Downloaded {len(all_data)}/{len(symbols)} stocks successfully")

    # Save cache
    with open(cache_file, 'wb') as f:
        pickle.dump(all_data, f)
    print(f"Cache saved to: {cache_file}")
    print()

    return all_data


# ============================================================================
# PATTERN DETECTION (from scanner_us.py, adapted for historical date)
# ============================================================================

def detect_patterns_at_date(symbol, all_data, scan_date):
    """
    Detect patterns at a specific historical date using cached data
    Returns list of pattern setups
    """
    if symbol not in all_data:
        return []

    df_full = all_data[symbol]['daily']
    df_weekly_full = all_data[symbol]['weekly']
    df_monthly_full = all_data[symbol].get('monthly')

    # Make scan_date timezone-aware to match yfinance data
    from datetime import timezone
    if scan_date.tzinfo is None:
        scan_date = scan_date.replace(tzinfo=timezone.utc)

    # Get data up to scan_date only (simulate being on that date)
    df = df_full[df_full.index <= scan_date].copy()
    df_w = df_weekly_full[df_weekly_full.index <= scan_date].copy() if df_weekly_full is not None else None
    df_m = df_monthly_full[df_monthly_full.index <= scan_date].copy() if df_monthly_full is not None else None

    if len(df) < 100:
        return []

    results = []

    # Cup & Handle — use the correct timeframe data for each
    # Daily: daily bars, Weekly: weekly bars, Monthly: monthly bars
    timeframe_data = {
        'Daily': df,
        'Weekly': df_w,
        'Monthly': df_m,
    }
    for timeframe in ['Daily', 'Weekly', 'Monthly']:
        tf_df = timeframe_data[timeframe]
        if tf_df is None or len(tf_df) < 40:
            continue
        r = detect_cup_handle_at(tf_df, timeframe, df_w)
        if r:
            r['symbol'] = symbol
            r['timeframe'] = timeframe
            results.append(r)

    # Double Bottom (uses daily data)
    r = detect_double_bottom_at(df, df_w)
    if r:
        r['symbol'] = symbol
        r['timeframe'] = 'Daily'
        results.append(r)

    # --- NEW PATTERNS (all use daily data) ---
    # Each detector gets df with ATR column, df_weekly for MTF check
    new_detectors = [
        detect_bull_flag,
        detect_pennant,
        detect_ascending_triangle,
        detect_symmetrical_triangle,
        detect_falling_wedge,
        detect_channel_breakout,
        detect_rectangle,
        detect_double_top,
        detect_inverse_head_shoulders,
    ]

    for detector in new_detectors:
        r = detector(df, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w)
        if r:
            # Apply MTF confirmation
            r['mtf_confirmed'] = check_higher_trend(df_w) if df_w is not None else True
            r['symbol'] = symbol
            r['timeframe'] = 'Daily'
            results.append(r)

    return results


def detect_cup_handle_at(df, timeframe, df_weekly):
    """Cup & Handle detection at historical date"""
    try:
        cup_bars, handle_bars = CUP_HANDLE_WINDOWS[timeframe]
        if len(df) < cup_bars + handle_bars:
            return None
        
        cup_window = df.iloc[-cup_bars:]
        left_rim = cup_window['High'].iloc[:10].max()
        right_rim = cup_window['High'].iloc[-10:].max()
        cup_bottom = cup_window['Low'].min()
        cup_depth = (left_rim - cup_bottom) / left_rim
        
        if not (0.12 <= cup_depth <= 0.50):
            return None
        
        handle_window = df.iloc[-handle_bars:]
        handle_high = handle_window['High'].max()
        handle_low = handle_window['Low'].min()
        handle_depth = (handle_high - handle_low) / handle_high
        
        if handle_depth > 0.50:
            return None
        if (right_rim - handle_low) / right_rim > 0.15:
            return None
        
        breakout = right_rim
        cmp = df['Close'].iloc[-1]
        
        structural_stop = handle_low
        atr = df['ATR'].iloc[-1]
        atr_stop = breakout - (atr * ATR_MULTIPLIER)
        
        stop_loss = max(structural_stop, atr_stop)
        max_stop = breakout * (1 - MAX_RISK_PCT)
        stop_loss = max(stop_loss, max_stop)
        
        risk_pct = (breakout - stop_loss) / breakout
        if risk_pct > MAX_RISK_PCT:
            stop_loss = breakout * (1 - MAX_RISK_PCT)
            risk_pct = MAX_RISK_PCT
        
        measured_move = cup_depth * breakout
        target_1 = breakout + (measured_move * TARGET_1_PCT)
        target_2 = breakout + (measured_move * TARGET_2_PCT)
        
        upside_pct = (target_1 - breakout) / breakout
        rr = upside_pct / risk_pct if risk_pct > 0 else 0
        
        dist_to_breakout = (breakout - cmp) / cmp
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
        
        mtf = check_higher_trend(df_weekly) if df_weekly is not None else True
        
        return {
            'pattern': f'Cup & Handle ({timeframe})',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk_pct': risk_pct * 100,
            'rr': rr,
            'cmp': cmp,
            'mtf_confirmed': mtf,
        }
    except:
        return None


def detect_double_bottom_at(df, df_weekly):
    """Double Bottom detection at historical date"""
    try:
        lookback = 60
        if len(df) < lookback:
            return None
        
        window = df.iloc[-lookback:]
        lows = find_local_minima(window['Low'], order=3)
        if len(lows) < 2:
            return None
        
        b1_idx, b1_price = lows[-2]
        b2_idx, b2_price = lows[-1]
        
        if (b2_idx - b1_idx) < 15:
            return None
        if abs(b1_price - b2_price) / b1_price > 0.03:
            return None
        
        peak_window = window.iloc[b1_idx:b2_idx]
        if len(peak_window) == 0:
            return None
        
        peak_price = peak_window['High'].max()
        breakout = peak_price
        cmp = df['Close'].iloc[-1]
        
        if cmp < min(b1_price, b2_price):
            return None
        
        structural_stop = min(b1_price, b2_price)
        atr = df['ATR'].iloc[-1]
        atr_stop = breakout - (atr * ATR_MULTIPLIER)
        
        stop_loss = max(structural_stop, atr_stop)
        max_stop = breakout * (1 - MAX_RISK_PCT)
        stop_loss = max(stop_loss, max_stop)
        
        risk_pct = (breakout - stop_loss) / breakout
        if risk_pct > MAX_RISK_PCT:
            stop_loss = breakout * (1 - MAX_RISK_PCT)
            risk_pct = MAX_RISK_PCT
        
        measured_move = peak_price - min(b1_price, b2_price)
        target_1 = breakout + (measured_move * TARGET_1_PCT)
        target_2 = breakout + (measured_move * TARGET_2_PCT)
        
        upside_pct = (target_1 - breakout) / breakout
        rr = upside_pct / risk_pct if risk_pct > 0 else 0
        
        dist_to_breakout = (breakout - cmp) / cmp
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
        
        mtf = check_higher_trend(df_weekly) if df_weekly is not None else True
        
        return {
            'pattern': 'Double Bottom',
            'status': status,
            'entry': breakout,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk_pct': risk_pct * 100,
            'rr': rr,
            'cmp': cmp,
            'mtf_confirmed': mtf,
        }
    except:
        return None


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class Trade:
    def __init__(self, symbol, pattern, entry_date, entry_price, stop, t1, t2, mtf):
        self.symbol = symbol
        self.pattern = pattern
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.stop = stop
        self.t1 = t1
        self.t2 = t2
        self.mtf = mtf
        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_pct = 0
        self.days_held = 0


def run_backtest(symbols, years, capital=10000, mtf_only=True, visual=False, refresh=False):
    """Run backtest using cached data"""

    print("=" * 70)
    print(f"VISUAL BACKTEST - scanner-us v2.0")
    print("=" * 70)
    print(f"Stocks: {len(symbols)} | Years: {years} | Capital: ${capital:,.0f}")
    print(f"MTF only: {mtf_only} | Scan interval: {SCAN_INTERVAL} days")
    if refresh:
        print(f"Cache: INCREMENTAL REFRESH (only download new stocks)")
    print("=" * 70)
    print()

    # Step 1: Download/cache data
    all_data = download_and_cache(symbols, years, refresh=refresh)
    
    # Step 2: Generate scan dates (every SCAN_INTERVAL days, starting from first Monday)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    # Find first Monday on or after start_date
    scan_dates = []
    current = start_date
    while current.weekday() != 0:  # 0 = Monday
        current += timedelta(days=1)
    
    # Now add every SCAN_INTERVAL days from first Monday
    while current <= end_date:
        scan_dates.append(current)
        current += timedelta(days=SCAN_INTERVAL)
    
    print(f"Scan dates: {len(scan_dates)} (every {SCAN_INTERVAL} days)")
    print()
    
    # Step 3: Run backtest
    open_trades = []
    closed_trades = []
    equity_curve = []
    current_capital = capital
    
    start_time = time.time()
    
    for scan_idx, scan_date in enumerate(scan_dates):
        elapsed = time.time() - start_time
        progress = (scan_idx + 1) / len(scan_dates) * 100
        
        # Close open trades
        for trade in list(open_trades):
            if trade.symbol not in all_data:
                continue
            
            df = all_data[trade.symbol]['daily']
            # Make scan_date timezone-aware for comparison
            from datetime import timezone
            sd = scan_date
            if sd.tzinfo is None:
                sd = sd.replace(tzinfo=timezone.utc)
            future = df[(df.index > trade.entry_date) & (df.index <= sd)]
            
            if future.empty:
                continue
            
            # Check stop loss
            if future['Low'].min() <= trade.stop:
                exit_date = future[future['Low'] <= trade.stop].index[0]
                trade.exit_date = exit_date
                trade.exit_price = trade.stop
                trade.exit_reason = 'LOSS'
                trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
                trade.days_held = (exit_date - trade.entry_date).days
                open_trades.remove(trade)
                closed_trades.append(trade)
                continue
            
            # Check target 1
            if future['High'].max() >= trade.t1:
                exit_date = future[future['High'] >= trade.t1].index[0]
                trade.exit_date = exit_date
                trade.exit_price = trade.t1
                trade.exit_reason = 'WIN_T1'
                trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
                trade.days_held = (exit_date - trade.entry_date).days
                open_trades.remove(trade)
                closed_trades.append(trade)
                continue
            
            # Time exit
            entry_date_naive = trade.entry_date.tz_localize(None) if trade.entry_date.tzinfo else trade.entry_date
            if (scan_date - entry_date_naive).days >= MAX_HOLD_DAYS:
                trade.exit_date = scan_date
                trade.exit_price = future['Close'].iloc[-1]
                trade.exit_reason = 'TIME_EXIT'
                trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
                trade.days_held = (scan_date - entry_date_naive).days
                open_trades.remove(trade)
                closed_trades.append(trade)
                continue
        
        # Scan for new setups
        new_entries = 0
        for symbol in symbols:
            if any(t.symbol == symbol for t in open_trades):
                continue
            
            setups = detect_patterns_at_date(symbol, all_data, scan_date)
            if not setups:
                continue
            
            # Filter: BREAKOUT only, MTF confirmed if required
            valid = [s for s in setups if s['status'] == 'BREAKOUT']
            if mtf_only:
                valid = [s for s in valid if s.get('mtf_confirmed', False)]
            
            if not valid:
                continue
            
            best = max(valid, key=lambda x: x.get('rr', 0))
            
            # Enter next day
            if symbol not in all_data:
                continue
            df = all_data[symbol]['daily']
            from datetime import timezone
            sd = scan_date
            if sd.tzinfo is None:
                sd = sd.replace(tzinfo=timezone.utc)
            future = df[df.index > sd]
            if future.empty:
                continue
            
            entry_date = future.index[0]
            entry_price = future['Open'].iloc[0]
            
            # BUG FIX: If entry gaps above T1, skip (no edge)
            # If entry gaps above breakout, use breakout as entry
            if entry_price > best['target_1']:
                continue  # Gapped above target - no trade
            
            # Use breakout as entry if stock gapped up above breakout
            actual_entry = min(entry_price, best['entry'])
            
            trade = Trade(
                symbol=symbol, pattern=best['pattern'],
                entry_date=entry_date, entry_price=actual_entry,
                stop=best['stop_loss'], t1=best['target_1'],
                t2=best['target_2'], mtf=best.get('mtf_confirmed', False)
            )
            open_trades.append(trade)
            new_entries += 1
        
        # Update equity
        realized = sum(t.pnl_pct for t in closed_trades) / 100 * capital
        current_capital = capital + realized
        equity_curve.append((scan_date, current_capital, len(open_trades), len(closed_trades)))
        
        print(f"[{scan_idx+1}/{len(scan_dates)}] {scan_date.strftime('%Y-%m-%d')} | "
              f"{progress:.0f}% | Open:{len(open_trades)} Closed:{len(closed_trades)} "
              f"| New:{new_entries} | Equity:${current_capital:,.0f}")
    
    # Close remaining trades
    for trade in open_trades:
        if trade.symbol in all_data:
            df = all_data[trade.symbol]['daily']
            trade.exit_date = df.index[-1]
            trade.exit_price = df['Close'].iloc[-1]
            trade.exit_reason = 'BACKTEST_END'
            trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
            entry_date_naive = trade.entry_date.tz_localize(None) if trade.entry_date.tzinfo else trade.entry_date
            exit_date_naive = trade.exit_date.tz_localize(None) if trade.exit_date.tzinfo else trade.exit_date
            trade.days_held = (exit_date_naive - entry_date_naive).days
            closed_trades.append(trade)
    
    elapsed_total = (time.time() - start_time) / 60
    print()
    print(f"Backtest complete in {elapsed_total:.1f} minutes")
    print()
    
    # Step 4: Calculate stats
    total = len(closed_trades)
    if total == 0:
        print("No trades found.")
        return
    
    wins = [t for t in closed_trades if t.pnl_pct > 0]
    losses = [t for t in closed_trades if t.pnl_pct <= 0]
    
    win_rate = len(wins) / total * 100
    avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
    expectancy = np.mean([t.pnl_pct for t in closed_trades])
    
    total_gains = sum(t.pnl_pct for t in wins)
    total_losses_abs = abs(sum(t.pnl_pct for t in losses))
    profit_factor = total_gains / total_losses_abs if total_losses_abs > 0 else 0
    
    final_capital = capital + sum(t.pnl_pct for t in closed_trades) / 100 * capital
    total_return = (final_capital - capital) / capital * 100
    cagr = ((final_capital / capital) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # Max drawdown
    equities = [e[1] for e in equity_curve]
    peak = capital
    max_dd = 0
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    # Print results
    print("=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    print()
    print(f"Total trades:      {total}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Win rate:          {win_rate:.1f}%")
    print(f"Avg win:           {avg_win:+.1f}%")
    print(f"Avg loss:          {avg_loss:+.1f}%")
    print(f"Expectancy:        {expectancy:+.2f}% per trade")
    print(f"Profit factor:     {profit_factor:.2f}")
    print(f"Max drawdown:      {max_dd:.1f}%")
    print()
    print(f"Starting capital:  ${capital:,.0f}")
    print(f"Final capital:     ${final_capital:,.0f}")
    print(f"Total return:      {total_return:+.1f}%")
    print(f"CAGR:              {cagr:+.1f}%")
    print()
    
    # Exit reason breakdown
    reasons = {}
    for t in closed_trades:
        r = t.exit_reason
        if r not in reasons:
            reasons[r] = {'count': 0, 'pnl': []}
        reasons[r]['count'] += 1
        reasons[r]['pnl'].append(t.pnl_pct)
    
    print("Exit reasons:")
    for r, d in reasons.items():
        avg = np.mean(d['pnl'])
        print(f"  {r:<15} {d['count']:>4} trades | avg {avg:+.1f}%")
    print()
    
    # Pattern breakdown
    patterns = {}
    for t in closed_trades:
        p = t.pattern
        if p not in patterns:
            patterns[p] = {'count': 0, 'wins': 0, 'pnl': []}
        patterns[p]['count'] += 1
        if t.pnl_pct > 0:
            patterns[p]['wins'] += 1
        patterns[p]['pnl'].append(t.pnl_pct)
    
    print("Pattern breakdown:")
    for p, d in sorted(patterns.items(), key=lambda x: len(x[1]['pnl']), reverse=True):
        wr = d['wins'] / d['count'] * 100
        exp = np.mean(d['pnl'])
        print(f"  {p:<30} {d['count']:>4} trades | {wr:>5.1f}% WR | {exp:+6.2f}% exp")
    print()
    
    # Sample trades
    print("Sample trades (last 15):")
    for t in closed_trades[-15:]:
        mtf = "[MTF]" if t.mtf else "[---]"
        print(f"  {t.symbol:6} {t.entry_date.strftime('%Y-%m-%d')} -> {t.exit_date.strftime('%Y-%m-%d')} "
              f"| {t.exit_reason:12} | {t.pnl_pct:+6.1f}% ({t.days_held:>3}d) {mtf}")
    print()
    
    # Save trades
    df_trades = pd.DataFrame([{
        'symbol': t.symbol, 'pattern': t.pattern,
        'entry_date': t.entry_date, 'entry_price': t.entry_price,
        'exit_date': t.exit_date, 'exit_price': t.exit_price,
        'exit_reason': t.exit_reason, 'pnl_pct': t.pnl_pct,
        'days_held': t.days_held, 'mtf': t.mtf,
    } for t in closed_trades])
    
    output = f"backtest_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_trades.to_csv(output, index=False)
    print(f"Trades saved to: {output}")
    
    # Step 5: Visual equity curve
    if visual and equity_curve:
        plot_equity_curve(equity_curve, capital, closed_trades, total_return, win_rate)
    
    return closed_trades


def plot_equity_curve(equity_curve, capital, trades, total_return, win_rate):
    """Plot equity curve with trade markers"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     facecolor='#0e0e0e')
    
    dates = [e[0] for e in equity_curve]
    equity = [e[1] for e in equity_curve]
    
    # Equity curve
    ax1.plot(dates, equity, color='#00ff00', linewidth=2, label='Equity')
    ax1.axhline(capital, color='#888888', linestyle='--', alpha=0.5, label=f'Start: ${capital:,.0f}')
    ax1.fill_between(dates, capital, equity, 
                     where=[e > capital for e in equity],
                     color='#00ff0030', alpha=0.5)
    ax1.fill_between(dates, capital, equity,
                     where=[e <= capital for e in equity],
                     color='#ff000030', alpha=0.5)
    
    # Mark wins and losses
    for t in trades:
        if t.exit_date and t.entry_date:
            color = '#00ff00' if t.pnl_pct > 0 else '#ff0000'
            # Normalize exit_date to tz-naive for comparison
            exit_d = t.exit_date
            if hasattr(exit_d, 'tzinfo') and exit_d.tzinfo is not None:
                exit_d = exit_d.tz_localize(None)
            # Find equity at exit date
            cum_pnl = sum(x.pnl_pct for x in trades
                         if x.exit_date is not None
                         and (x.exit_date.tz_localize(None) if hasattr(x.exit_date, 'tzinfo') and x.exit_date.tzinfo else x.exit_date) <= exit_d)
            ax1.scatter(exit_d, capital + cum_pnl / 100 * capital,
                       color=color, s=30, alpha=0.6, zorder=5)
    
    ax1.set_title(f'Backtest Equity Curve | Return: {total_return:+.1f}% | Win Rate: {win_rate:.1f}%',
                 fontsize=14, fontweight='bold', color='white', pad=15)
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12, color='#cccccc')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.2, linestyle=':')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Trade count over time
    open_counts = [e[2] for e in equity_curve]
    closed_counts = [e[3] for e in equity_curve]
    ax2.plot(dates, closed_counts, color='#00ffff', linewidth=1.5, label='Closed trades')
    ax2.plot(dates, open_counts, color='#ffff00', linewidth=1, alpha=0.7, label='Open trades')
    ax2.set_ylabel('Trade Count', fontsize=10, color='#cccccc')
    ax2.set_xlabel('Date', fontsize=10, color='#cccccc')
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.2, linestyle=':')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    chart_file = f"backtest_equity_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(chart_file, dpi=150, facecolor='#0e0e0e', bbox_inches='tight')
    print(f"Equity curve saved to: {chart_file}")
    plt.close()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Visual Backtest (cached data)')
    parser.add_argument('--stocks', default='backbone_us.txt')
    parser.add_argument('--years', type=int, default=2)
    parser.add_argument('--capital', type=float, default=10000)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--mtf-only', action='store_true', default=True)
    parser.add_argument('--no-mtf', action='store_true', help='Include non-MTF trades')
    parser.add_argument('--visual', action='store_true', help='Generate equity curve chart')
    parser.add_argument('--refresh-cache', action='store_true',
                        help='Incremental refresh: only download NEW stocks not in cache, merge into existing cache')
    args = parser.parse_args()

    with open(args.stocks, 'r') as f:
        symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if args.test:
        symbols = symbols[:10]
        args.years = 1

    mtf_only = not args.no_mtf

    run_backtest(symbols, args.years, args.capital, mtf_only, args.visual,
                 refresh=args.refresh_cache)


if __name__ == '__main__':
    main()
