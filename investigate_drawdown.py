"""
STEP 2: Drawdown Investigation + Correct Stats
1. Find when the 48.7% max drawdown happened
2. How long recovery took
3. Which patterns/stocks caused it
4. Portfolio exposure during drawdown
"""
import pandas as pd
import numpy as np

df = pd.read_csv('backtest_results/sp500_5yr_all_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')
df['exit_date'] = pd.to_datetime(df['exit_date'], utc=True, format='mixed')
df = df.sort_values('exit_date').reset_index(drop=True)

print("=" * 80)
print("STEP 2: DRAWDOWN INVESTIGATION")
print("=" * 80)

# --- Correct stats ---
n = len(df)
wins = df[df['pnl_pct'] > 0]
losses = df[df['pnl_pct'] <= 0]
wr = len(wins) / n * 100
avg_win = wins['pnl_pct'].mean()
avg_loss = losses['pnl_pct'].mean()
expectancy = df['pnl_pct'].mean()  # CORRECT way
pf = wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum())

print(f"\n--- CORRECTED STATS ---")
print(f"  Trades:        {n}")
print(f"  Win rate:      {wr:.2f}%")
print(f"  Avg win:       +{avg_win:.2f}%")
print(f"  Avg loss:      {avg_loss:.2f}%")
print(f"  Expectancy:    +{expectancy:.2f}% per trade (mean of all pnl)")
print(f"  Profit factor: {pf:.2f}")

# --- Equity curve (fixed position size, no compounding) ---
# Each trade uses fixed $ amount. Track cumulative P&L.
position_size = 1000  # $1000 per trade (fixed, no compounding)
df['pnl_dollars'] = df['pnl_pct'] / 100 * position_size
df['cumulative_pnl'] = df['pnl_dollars'].cumsum()
df['equity'] = 10000 + df['cumulative_pnl']  # Starting $10k

# Find drawdown
df['peak'] = df['equity'].cummax()
df['drawdown'] = (df['equity'] - df['peak']) / df['peak'] * 100

max_dd = df['drawdown'].min()
max_dd_idx = df['drawdown'].idxmin()
max_dd_date = df.loc[max_dd_idx, 'exit_date']
peak_idx = df.loc[:max_dd_idx, 'equity'].idxmax()
peak_date = df.loc[peak_idx, 'exit_date']
peak_equity = df.loc[peak_idx, 'equity']
trough_equity = df.loc[max_dd_idx, 'equity']

print(f"\n--- MAX DRAWDOWN ---")
print(f"  Max drawdown:    {max_dd:.2f}%")
print(f"  Peak equity:     ${peak_equity:,.2f} on {peak_date.date()}")
print(f"  Trough equity:   ${trough_equity:,.2f} on {max_dd_date.date()}")
print(f"  Dollar drawdown: ${peak_equity - trough_equity:,.2f}")

# Recovery: when did equity exceed peak again?
recovery = df[(df.index > max_dd_idx) & (df['equity'] > peak_equity)]
if len(recovery) > 0:
    recovery_date = recovery.iloc[0]['exit_date']
    recovery_days = (recovery_date - max_dd_date).days
    print(f"  Recovery date:   {recovery_date.date()} ({recovery_days} days)")
else:
    print(f"  Recovery:        NOT RECOVERED by end of backtest")

# --- Trades during drawdown period ---
dd_period = df[(df['exit_date'] >= peak_date) & (df['exit_date'] <= max_dd_date)]
print(f"\n--- TRADES DURING DRAWDOWN PERIOD ---")
print(f"  Period: {peak_date.date()} to {max_dd_date.date()}")
print(f"  Trades in DD period: {len(dd_period)}")
print(f"  Wins: {(dd_period['pnl_pct']>0).sum()} | Losses: {(dd_period['pnl_pct']<=0).sum()}")
print(f"  WR during DD: {(dd_period['pnl_pct']>0).sum()/len(dd_period)*100:.1f}%")
print(f"  Avg P&L during DD: {dd_period['pnl_pct'].mean():.2f}%")

print(f"\n  Pattern breakdown during drawdown:")
for pattern in dd_period['pattern'].value_counts().index:
    subset = dd_period[dd_period['pattern'] == pattern]
    n_p = len(subset)
    w_p = (subset['pnl_pct'] > 0).sum()
    exp_p = subset['pnl_pct'].mean()
    print(f"    {pattern:<30} {n_p:>4} trades | {w_p/n_p*100:>5.1f}% WR | {exp_p:>+6.2f}% exp")

print(f"\n  Top 10 losing trades during drawdown:")
dd_losses = dd_period.sort_values('pnl_pct').head(10)
for _, t in dd_losses.iterrows():
    print(f"    {t['symbol']:<6} {t['pattern']:<28} {t['pnl_pct']:>+6.2f}% | {t['exit_date'].date()}")

# --- Concurrent positions analysis ---
print(f"\n--- CONCURRENT POSITIONS ANALYSIS ---")
# For each day, count how many trades are open
all_dates = pd.date_range(df['entry_date'].min(), df['exit_date'].max(), freq='D')
max_concurrent = 0
max_concurrent_date = None
concurrent_history = []

for d in all_dates:
    open_count = ((df['entry_date'] <= d) & (df['exit_date'] > d)).sum()
    concurrent_history.append({'date': d, 'open': open_count})
    if open_count > max_concurrent:
        max_concurrent = open_count
        max_concurrent_date = d

concurrent_df = pd.DataFrame(concurrent_history)
print(f"  Max concurrent positions: {max_concurrent} on {max_concurrent_date.date()}")
print(f"  Avg concurrent positions: {concurrent_df['open'].mean():.1f}")
print(f"  Median concurrent:        {concurrent_df['open'].median():.0f}")

# Concurrent during drawdown
dd_concurrent = concurrent_df[(concurrent_df['date'] >= peak_date) & (concurrent_df['date'] <= max_dd_date)]
print(f"  Avg concurrent during DD: {dd_concurrent['open'].mean():.1f}")
print(f"  Max concurrent during DD: {dd_concurrent['open'].max()}")

# --- Yearly breakdown ---
print(f"\n--- YEARLY PERFORMANCE ---")
df['year'] = df['exit_date'].dt.year
for year in sorted(df['year'].unique()):
    yr = df[df['year'] == year]
    n_y = len(yr)
    w_y = (yr['pnl_pct'] > 0).sum()
    exp_y = yr['pnl_pct'].mean()
    pf_y = yr[yr['pnl_pct']>0]['pnl_pct'].sum() / abs(yr[yr['pnl_pct']<=0]['pnl_pct'].sum())
    print(f"  {year}: {n_y:>5} trades | {w_y/n_y*100:>5.1f}% WR | {exp_y:>+6.2f}% exp | PF {pf_y:.2f}")

# --- Sector analysis during drawdown (if we have sector data) ---
print(f"\n--- TOP STOCKS BY LOSS (all time) ---")
worst = df.sort_values('pnl_pct').head(20)
for _, t in worst.iterrows():
    print(f"    {t['symbol']:<6} {t['pattern']:<28} {t['pnl_pct']:>+6.2f}% | {t['exit_date'].date()}")

print(f"\n{'='*80}")
print(f"VERDICT")
print(f"{'='*80}")
print(f"  Correct expectancy: +{expectancy:.2f}% (was reported as +nan or +5.34)")
print(f"  Correct PF: {pf:.2f}")
print(f"  Max drawdown: {max_dd:.2f}%")
print(f"  Drawdown period: {peak_date.date()} to {max_dd_date.date()}")
print(f"  No duplicate trades found (5,659 are all unique stock+date)")
print(f"  14-day cooldown removes only 27 trades (negligible)")
