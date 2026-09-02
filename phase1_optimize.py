"""
Phase 1: Trade Profitability Optimization
Re-run backtest with different SL/target/hold parameters.
Uses the cached price data + pattern detectors.

Instead of re-detecting patterns (slow), we re-simulate each trade
using the entry_date and entry_price from the existing backtest,
but with different SL/target/hold parameters.

We need to re-calculate SL and target for each trade based on the
original pattern detection. To do this efficiently, we re-run the
detectors on the cached data at each trade's entry date.
"""
import pandas as pd
import numpy as np
import pickle
import os
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Load price data
print("Loading price data cache...")
cache_file = 'backtest_cache/all_stocks_5y.pkl'
with open(cache_file, 'rb') as f:
    all_data = pickle.load(f)
print(f"Loaded {len(all_data)} stocks")

# Load existing trades to get entry dates + symbols + patterns
df = pd.read_csv('backtest_results/sp500_5yr_cleaned_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')
df['exit_date'] = pd.to_datetime(df['exit_date'], utc=True, format='mixed')

print(f"Base data: {len(df)} trades")

# Import pattern detectors
from scanner_us import calculate_atr, CUP_HANDLE_WINDOWS, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT
from patterns import (
    detect_bull_flag, detect_pennant,
    detect_ascending_triangle, detect_falling_wedge,
    detect_channel_breakout, detect_double_top, detect_inverse_head_shoulders,
)

# Re-detect patterns at each trade's entry date to get SL/target
print("Re-detecting patterns to get SL/target for each trade...")

detectors_map = {
    'Falling Wedge': detect_falling_wedge,
    'Inverse Head & Shoulders': detect_inverse_head_shoulders,
    'Channel Breakout': detect_channel_breakout,
    'Ascending Triangle': detect_ascending_triangle,
    'Double Bottom': None,  # from scanner_us.py
    'Double Top Breakout': detect_double_top,
    'Cup & Handle (Weekly)': None,  # from scanner_us.py
}

# For Double Bottom and C&H, we need to import from scanner_us
from scanner_us import detect_double_bottom, detect_cup_and_handle

# Build a lookup: (symbol, entry_date, pattern) -> {entry, stop_loss, target_1, target_2, measured_move, atr}
trade_params = {}
sample_size = min(len(df), 2000)  # Sample for speed
df_sample = df.sample(n=sample_size, random_state=42)

t0 = time.time()
for idx, (_, trade) in enumerate(df_sample.iterrows()):
    if idx % 200 == 0:
        print(f"  Progress: {idx}/{sample_size} ({idx/sample_size*100:.0f}%)")

    symbol = trade['symbol']
    pattern = trade['pattern']
    entry_date = trade['entry_date']

    if symbol not in all_data:
        continue

    df_full = all_data[symbol]['daily']
    df_slice = df_full[df_full.index <= entry_date].copy()

    if len(df_slice) < 80:
        continue

    # Get weekly data
    df_w = all_data[symbol].get('weekly')
    if df_w is not None:
        df_w_slice = df_w[df_w.index <= entry_date]
    else:
        df_w_slice = None

    # Calculate ATR
    atr = calculate_atr(df_slice)

    # Run the appropriate detector
    result = None
    if pattern == 'Falling Wedge':
        result = detect_falling_wedge(df_slice, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w_slice)
    elif pattern == 'Inverse Head & Shoulders':
        result = detect_inverse_head_shoulders(df_slice, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w_slice)
    elif pattern == 'Channel Breakout':
        result = detect_channel_breakout(df_slice, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w_slice)
    elif pattern == 'Ascending Triangle':
        result = detect_ascending_triangle(df_slice, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w_slice)
    elif pattern == 'Double Top Breakout':
        result = detect_double_top(df_slice, ATR_MULTIPLIER, MAX_RISK_PCT, TARGET_1_PCT, TARGET_2_PCT, df_w_slice)
    elif pattern == 'Double Bottom':
        # Double Bottom is in scanner_us.py
        result = detect_double_bottom(df_slice, df_w_slice)
    elif pattern == 'Cup & Handle (Weekly)':
        if df_w_slice is not None and len(df_w_slice) >= 40:
            result = detect_cup_and_handle(df_w_slice, 'Weekly', df_w_slice)

    if result:
        key = (symbol, entry_date, pattern)
        trade_params[key] = {
            'entry': result.get('entry', result.get('breakout', trade['entry_price'])),
            'stop_loss': result.get('stop_loss', result.get('sl')),
            'target_1': result.get('target_1', result.get('t1')),
            'target_2': result.get('target_2', result.get('t2')),
            'measured_move': result.get('measured_move', 0),
            'atr': atr,
        }

t1 = time.time()
print(f"Re-detected {len(trade_params)} trades in {t1-t0:.1f}s")

# Now re-simulate with different parameters
def resimulate(trade_row, sl_method, target_method, max_hold, costs_pct=0.2):
    """Re-simulate a single trade with different SL/target/hold."""
    symbol = trade_row['symbol']
    pattern = trade_row['pattern']
    entry_date = trade_row['entry_date']
    entry_price = trade_row['entry_price']

    key = (symbol, entry_date, pattern)
    if key not in trade_params:
        return None

    params = trade_params[key]
    original_sl = params['stop_loss']
    original_t1 = params['target_1']
    original_t2 = params['target_2']
    atr = params['atr']
    breakout = params['entry']

    if not original_sl or not original_t1 or np.isnan(original_sl) or np.isnan(original_t1):
        return None

    risk_amt = breakout - original_sl

    # New stop loss
    if sl_method == 'atr_1.5x':
        new_sl = breakout - (risk_amt * 0.75)
    elif sl_method == 'atr_2x':
        new_sl = original_sl
    elif sl_method == 'atr_2.5x':
        new_sl = breakout - (risk_amt * 1.25)
    elif sl_method == 'fixed_5':
        new_sl = breakout * 0.95
    elif sl_method == 'fixed_8':
        new_sl = breakout * 0.92
    elif sl_method == 'fixed_10':
        new_sl = breakout * 0.90
    else:
        new_sl = original_sl

    # New target
    full_move = 2 * (original_t1 - breakout)  # T1 is 50% of move
    if target_method == 'pct25':
        new_t1 = breakout + full_move * 0.25
    elif target_method == 'pct50':
        new_t1 = original_t1
    elif target_method == 'pct75':
        new_t1 = breakout + full_move * 0.75
    elif target_method == 'pct100':
        new_t1 = original_t2 if original_t2 else breakout + full_move
    elif target_method == 'rr_2':
        new_t1 = breakout + (breakout - new_sl) * 2
    elif target_method == 'rr_3':
        new_t1 = breakout + (breakout - new_sl) * 3
    else:
        new_t1 = original_t1

    # Get future prices
    if symbol not in all_data:
        return None
    df_sym = all_data[symbol]['daily']
    future = df_sym[df_sym.index > entry_date]
    if future.empty:
        return None

    # Simulate
    for i in range(min(len(future), max_hold)):
        row = future.iloc[i]
        date = future.index[i]

        if row['Low'] <= new_sl:
            pnl = (new_sl - entry_price) / entry_price * 100 - costs_pct
            return {'pnl_pct': pnl, 'exit_reason': 'LOSS', 'days_held': (date - entry_date).days, 'pattern': pattern}

        if row['High'] >= new_t1:
            pnl = (new_t1 - entry_price) / entry_price * 100 - costs_pct
            return {'pnl_pct': pnl, 'exit_reason': 'WIN_T1', 'days_held': (date - entry_date).days, 'pattern': pattern}

    # Time exit
    last_idx = min(len(future) - 1, max_hold - 1)
    last_row = future.iloc[last_idx]
    pnl = (last_row['Close'] - entry_price) / entry_price * 100 - costs_pct
    return {'pnl_pct': pnl, 'exit_reason': 'TIME_EXIT', 'days_held': (future.index[last_idx] - entry_date).days, 'pattern': pattern}


def run_sweep(trades_df, sl_method, target_method, max_hold):
    """Run sweep on all trades with given parameters."""
    results = []
    for _, trade in trades_df.iterrows():
        r = resimulate(trade, sl_method, target_method, max_hold)
        if r:
            results.append(r)

    if not results:
        return None

    res_df = pd.DataFrame(results)
    n = len(res_df)
    wins = res_df[res_df['pnl_pct'] > 0]
    losses = res_df[res_df['pnl_pct'] <= 0]
    wr = len(wins) / n * 100
    exp = res_df['pnl_pct'].mean()
    pf = wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum()) if len(losses) > 0 else float('inf')
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    avg_hold = res_df['days_held'].mean()

    return {'n': n, 'wr': wr, 'exp': exp, 'pf': pf, 'avg_win': avg_win, 'avg_loss': avg_loss, 'avg_hold': avg_hold}


# Use only the sampled trades that we re-detected
valid_trades = df_sample[df_sample.apply(lambda r: (r['symbol'], r['entry_date'], r['pattern']) in trade_params, axis=1)]
print(f"Valid trades for sweep: {len(valid_trades)} (sampled from {len(df)})")

# --- TEST 1: Stop Loss Methods ---
print(f"\n{'='*80}")
print("TEST 1: STOP LOSS METHODS (target=50% measured move, 45-day exit)")
print(f"{'='*80}")
print(f"{'Method':<12} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'AvgWin':>8} {'AvgLoss':>9} {'AvgHold':>8}")
print(f"{'-'*70}")

sl_methods = ['atr_1.5x', 'atr_2x', 'atr_2.5x', 'fixed_5', 'fixed_8', 'fixed_10']
sl_results = {}
for sl in sl_methods:
    r = run_sweep(valid_trades, sl, 'pct50', 45)
    sl_results[sl] = r
    if r:
        print(f"{sl:<12} {r['n']:>7} {r['wr']:>6.1f}% {r['exp']:>+7.2f}% {r['pf']:>6.2f} {r['avg_win']:>+7.2f}% {r['avg_loss']:>+8.2f}% {r['avg_hold']:>7.1f}d")

# --- TEST 2: Target Methods ---
print(f"\n{'='*80}")
print("TEST 2: TARGET METHODS (SL=ATR 2x, 45-day exit)")
print(f"{'='*80}")
print(f"{'Method':<12} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'AvgWin':>8} {'AvgLoss':>9} {'AvgHold':>8}")
print(f"{'-'*70}")

target_methods = ['pct25', 'pct50', 'pct75', 'pct100', 'rr_2', 'rr_3']
target_results = {}
for t in target_methods:
    r = run_sweep(valid_trades, 'atr_2x', t, 45)
    target_results[t] = r
    if r:
        print(f"{t:<12} {r['n']:>7} {r['wr']:>6.1f}% {r['exp']:>+7.2f}% {r['pf']:>6.2f} {r['avg_win']:>+7.2f}% {r['avg_loss']:>+8.2f}% {r['avg_hold']:>7.1f}d")

# --- TEST 3: Max Hold Period ---
print(f"\n{'='*80}")
print("TEST 3: MAX HOLD PERIOD (SL=ATR 2x, target=50% measured move)")
print(f"{'='*80}")
print(f"{'Days':<12} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'AvgWin':>8} {'AvgLoss':>9} {'AvgHold':>8}")
print(f"{'-'*70}")

hold_periods = [20, 30, 45, 60, 90, 120]
hold_results = {}
for h in hold_periods:
    r = run_sweep(valid_trades, 'atr_2x', 'pct50', h)
    hold_results[h] = r
    if r:
        print(f"{h}d{'':<9} {r['n']:>7} {r['wr']:>6.1f}% {r['exp']:>+7.2f}% {r['pf']:>6.2f} {r['avg_win']:>+7.2f}% {r['avg_loss']:>+8.2f}% {r['avg_hold']:>7.1f}d")

# --- TEST 4: Best Combinations ---
print(f"\n{'='*80}")
print("TEST 4: BEST COMBINATIONS (top 15 by PF)")
print(f"{'='*80}")

combos = []
for sl in sl_methods:
    for t in target_methods:
        for h in [30, 45, 60]:
            r = run_sweep(valid_trades, sl, t, h)
            if r and r['n'] > 50:
                combos.append({'sl': sl, 'target': t, 'hold': h, **r})

combos.sort(key=lambda x: x['pf'], reverse=True)

print(f"{'SL':<10} {'Target':<10} {'Hold':>6} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'AvgWin':>8} {'AvgLoss':>9}")
print(f"{'-'*80}")
for c in combos[:15]:
    print(f"{c['sl']:<10} {c['target']:<10} {c['hold']:>5}d {c['n']:>7} {c['wr']:>6.1f}% {c['exp']:>+7.2f}% {c['pf']:>6.2f} {c['avg_win']:>+7.2f}% {c['avg_loss']:>+8.2f}%")

# --- TEST 5: Best combo per pattern ---
print(f"\n{'='*80}")
print("TEST 5: BEST COMBO PER PATTERN (top 3 combos)")
print(f"{'='*80}")

top_3 = combos[:3]
for pattern in valid_trades['pattern'].value_counts().index:
    pattern_df = valid_trades[valid_trades['pattern'] == pattern]
    print(f"\n  {pattern} ({len(pattern_df)} trades):")
    print(f"  {'SL':<10} {'Target':<10} {'Hold':>6} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7}")
    for c in top_3:
        r = run_sweep(pattern_df, c['sl'], c['target'], c['hold'])
        if r:
            print(f"  {c['sl']:<10} {c['target']:<10} {c['hold']:>5}d {r['n']:>7} {r['wr']:>6.1f}% {r['exp']:>+7.2f}% {r['pf']:>6.2f}")

# --- SUMMARY ---
print(f"\n{'='*80}")
print("PHASE 1 SUMMARY")
print(f"{'='*80}")

if combos:
    best = combos[0]
    print(f"\nBest overall combination:")
    print(f"  SL: {best['sl']} | Target: {best['target']} | Hold: {best['hold']}d")
    print(f"  Trades: {best['n']} | WR: {best['wr']:.1f}% | Exp: {best['exp']:+.2f}% | PF: {best['pf']:.2f}")
    print(f"  Avg win: {best['avg_win']:+.2f}% | Avg loss: {best['avg_loss']:+.2f}%")
    print(f"  Avg hold: {best['avg_hold']:.1f} days")

    current = sl_results.get('atr_2x', {})
    if current:
        print(f"\nCurrent config (ATR 2x, 50% target, 45d):")
        print(f"  WR: {current['wr']:.1f}% | Exp: {current['exp']:+.2f}% | PF: {current['pf']:.2f}")
        print(f"\nImprovement with best combo:")
        print(f"  PF: {current['pf']:.2f} -> {best['pf']:.2f} ({(best['pf']/current['pf']-1)*100:+.1f}%)")
        print(f"  Exp: {current['exp']:+.2f}% -> {best['exp']:+.2f}% ({best['exp']-current['exp']:+.2f}%)")

# Save
import json
results_json = {
    'sl_methods': {k: v for k, v in sl_results.items() if v},
    'target_methods': {k: v for k, v in target_results.items() if v},
    'hold_periods': {str(k): v for k, v in hold_results.items() if v},
    'best_combos': [{k: v for k, v in c.items()} for c in combos[:10]],
}
with open('backtest_results/phase1_optimization.json', 'w') as f:
    json.dump(results_json, f, indent=2, default=str)
print(f"\nSaved: backtest_results/phase1_optimization.json")
