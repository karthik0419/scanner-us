"""
STEP 3: Falling Wedge Visual Audit
Randomly sample 50 Falling Wedge detections, generate charts, and save for manual inspection.
Also check how loose the detector is by measuring pattern statistics.
"""
import pandas as pd
import numpy as np
import pickle
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Load backtest trades
df = pd.read_csv('backtest_results/sp500_5yr_all_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')

# Filter to Falling Wedge trades
fw = df[df['pattern'] == 'Falling Wedge'].copy()
print(f"Total Falling Wedge trades: {len(fw)}")

# Random sample 50
sample = fw.sample(n=min(50, len(fw)), random_state=42)
print(f"Sampling {len(sample)} for visual inspection")

# Load cache
cache_file = 'backtest_cache/all_stocks_5y.pkl'
with open(cache_file, 'rb') as f:
    all_data = pickle.load(f)

# Create output directory
os.makedirs('wedge_audit', exist_ok=True)

# Generate charts for each sample
from patterns.wedge import detect_falling_wedge

audit_results = []
for i, (idx, trade) in enumerate(sample.iterrows()):
    symbol = trade['symbol']
    entry_date = trade['entry_date']

    if symbol not in all_data:
        continue

    df_full = all_data[symbol]['daily']

    # Get data up to entry date (simulate being on that date)
    df_slice = df_full[df_full.index <= entry_date].copy()
    if len(df_slice) < 80:
        continue

    # Run detector to get the pattern details
    result = detect_falling_wedge(df_slice, 2.0, 0.08, 0.5, 1.0)
    if not result:
        continue

    # Get the window used (40-120 bars)
    # Show last 80 bars of price + pattern levels
    chart_data = df_slice.tail(80)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})

    # Price chart
    ax1.plot(chart_data.index, chart_data['Close'], 'b-', linewidth=1, label='Close')
    ax1.plot(chart_data.index, chart_data['High'], 'g-', linewidth=0.5, alpha=0.3, label='High')
    ax1.plot(chart_data.index, chart_data['Low'], 'r-', linewidth=0.5, alpha=0.3, label='Low')

    # Entry, SL, T1 lines
    ax1.axhline(y=result['entry'], color='orange', linestyle='--', label=f"Breakout: ${result['entry']:.2f}")
    ax1.axhline(y=result['stop_loss'], color='red', linestyle='--', label=f"SL: ${result['stop_loss']:.2f}")
    ax1.axhline(y=result['target_1'], color='green', linestyle='--', label=f"T1: ${result['target_1']:.2f}")

    # Mark entry point
    ax1.axvline(x=entry_date, color='purple', linestyle=':', alpha=0.5)

    # Result
    pnl = trade['pnl_pct']
    color = 'green' if pnl > 0 else 'red'
    result_text = f"{'WIN' if pnl > 0 else 'LOSS'} {pnl:+.1f}%"

    ax1.set_title(f"{symbol} — Falling Wedge — {entry_date.date()} — {result_text}",
                  color=color, fontsize=11, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Volume
    ax2.bar(chart_data.index, chart_data['Volume'], width=1, alpha=0.5, color='gray')
    ax2.set_title('Volume', fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'wedge_audit/{i+1:02d}_{symbol}_{entry_date.date()}.png', dpi=100)
    plt.close()

    audit_results.append({
        'idx': i + 1,
        'symbol': symbol,
        'date': entry_date.date(),
        'status': result['status'],
        'entry': result['entry'],
        'sl': result['stop_loss'],
        't1': result['target_1'],
        'rr': result['rr'],
        'pnl': pnl,
        'win': pnl > 0,
    })

# Save audit summary
audit_df = pd.DataFrame(audit_results)
audit_df.to_csv('wedge_audit/audit_summary.csv', index=False)

print(f"\nGenerated {len(audit_results)} charts in wedge_audit/")
print(f"\nAudit Summary:")
print(f"  Wins: {audit_df['win'].sum()} | Losses: {(~audit_df['win']).sum()}")
print(f"  Avg P&L: {audit_df['pnl'].mean():.2f}%")
print(f"  Avg R:R: {audit_df['rr'].mean():.2f}")

# --- Statistical analysis of Falling Wedge detector ---
print(f"\n{'='*80}")
print(f"FALLING WEDGE DETECTOR STATISTICS (all 3,381 trades)")
print(f"{'='*80}")

# Check how wide the windows are
# Check R:R distribution
fw_all = df[df['pattern'] == 'Falling Wedge']
print(f"  R:R distribution:")
print(f"    Mean:   {fw_all['pnl_pct'].mean():.2f}% P&L")
print(f"    Median: {fw_all['pnl_pct'].median():.2f}% P&L")
print(f"    Std:    {fw_all['pnl_pct'].std():.2f}%")
print(f"    Min:    {fw_all['pnl_pct'].min():.2f}%")
print(f"    Max:    {fw_all['pnl_pct'].max():.2f}%")

# Check if trades are concentrated in certain periods
print(f"\n  Trades by year:")
fw_all['year'] = fw_all['entry_date'].dt.year
for year in sorted(fw_all['year'].unique()):
    yr = fw_all[fw_all['year'] == year]
    n_y = len(yr)
    w_y = (yr['pnl_pct'] > 0).sum()
    print(f"    {year}: {n_y:>5} trades | {w_y/n_y*100:.1f}% WR | {yr['pnl_pct'].mean():+.2f}% exp")

# Check trades per stock (is it detecting same stock repeatedly?)
print(f"\n  Trades per stock (top 20):")
stock_counts = fw_all['symbol'].value_counts().head(20)
for sym, count in stock_counts.items():
    sym_trades = fw_all[fw_all['symbol'] == sym]
    wr_sym = (sym_trades['pnl_pct'] > 0).sum() / len(sym_trades) * 100
    print(f"    {sym:<6} {count:>3} trades | {wr_sym:.0f}% WR | {sym_trades['pnl_pct'].mean():+.2f}% exp")

print(f"\n  Total unique stocks: {fw_all['symbol'].nunique()}")
print(f"  Avg trades per stock: {len(fw_all) / fw_all['symbol'].nunique():.1f}")
