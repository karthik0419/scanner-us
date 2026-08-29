"""Simulate 1-year trading with $1,000 starting capital using actual backtest trades."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

df = pd.read_csv('backtest_results/sp500_5yr_all_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True)

# The backtest spans ~5 years (Aug 2021 - Aug 2026)
# Let's simulate the LAST 1 year (Aug 2025 - Aug 2026)
# This is the most recent market regime — most realistic

print("=" * 70)
print("SIMULATION: $1,000 trading for 1 year")
print("=" * 70)

# Filter to last 1 year of trades
cutoff = df['entry_date'].max() - pd.Timedelta(days=365)
one_year = df[df['entry_date'] >= cutoff].copy()
one_year = one_year.sort_values('entry_date').reset_index(drop=True)

print(f"\nBacktest period: {one_year['entry_date'].min().date()} to {one_year['entry_date'].max().date()}")
print(f"Total trades in 1 year: {len(one_year)}")

# --- Scenario 1: Fixed position size (no compounding) ---
# Each trade uses a FIXED amount (e.g. 25% of starting capital = $250)
# This is how the backtest works — no compounding
print("\n" + "=" * 70)
print("SCENARIO 1: Fixed position size (no compounding)")
print("=" * 70)

starting_capital = 1000

# How many trades can we take? In reality, we can't take ALL trades
# because we have limited capital. Let's simulate with position sizing.

# With $1,000, let's assume:
# - Max 3 concurrent positions (diversification)
# - Each position = 33% of capital = ~$333
# - Enter trades in order, skip if 3 already open

# But first, let's see the simple math:
# If we took ALL trades with equal $ allocation:
total_pct = one_year['pnl_pct'].sum()
avg_exp = one_year['pnl_pct'].mean()
n_trades = len(one_year)
wins = (one_year['pnl_pct'] > 0).sum()
losses = (one_year['pnl_pct'] <= 0).sum()
wr = wins / n_trades * 100

print(f"\n  All {n_trades} trades (if unlimited capital):")
print(f"  Win rate: {wr:.1f}% ({wins}W / {losses}L)")
print(f"  Avg win: +{one_year[one_year['pnl_pct']>0]['pnl_pct'].mean():.1f}%")
print(f"  Avg loss: {one_year[one_year['pnl_pct']<=0]['pnl_pct'].mean():.1f}%")
print(f"  Sum of all trade returns: {total_pct:.1f}%")
print(f"  Avg expectancy per trade: {avg_exp:.2f}%")

# --- Scenario 2: Realistic simulation with $1,000 ---
# Max 3 concurrent positions, each = 1/3 of capital
# Compounding: after each trade, capital updates
print("\n" + "=" * 70)
print("SCENARIO 2: Realistic — $1,000, max 3 concurrent, compounding")
print("=" * 70)

capital = starting_capital
max_positions = 3
position_size_pct = 1.0 / max_positions  # 33% each
open_positions = []  # list of (entry_date, exit_date, pnl_pct, amount_invested)
trade_log = []

for _, trade in one_year.iterrows():
    # Close any positions that exited before this trade's entry
    still_open = []
    for pos in open_positions:
        if pos['exit_date'] <= trade['entry_date']:
            # Close this position
            pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
            capital += pnl_dollars
            trade_log.append({
                'symbol': pos['symbol'],
                'pattern': pos['pattern'],
                'entry': pos['entry_date'].date(),
                'exit': pos['exit_date'].date(),
                'pnl_pct': pos['pnl_pct'],
                'amount': pos['amount'],
                'pnl_dollars': pnl_dollars,
                'capital_after': capital,
            })
        else:
            still_open.append(pos)
    open_positions = still_open

    # Check if we can open a new position
    if len(open_positions) < max_positions:
        amount = capital * position_size_pct
        open_positions.append({
            'symbol': trade['symbol'],
            'pattern': trade['pattern'],
            'entry_date': trade['entry_date'],
            'exit_date': pd.to_datetime(trade['exit_date'], utc=True),
            'pnl_pct': trade['pnl_pct'],
            'amount': amount,
        })

# Close remaining open positions
for pos in open_positions:
    pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
    capital += pnl_dollars
    trade_log.append({
        'symbol': pos['symbol'],
        'pattern': pos['pattern'],
        'entry': pos['entry_date'].date(),
        'exit': pos['exit_date'].date(),
        'pnl_pct': pos['pnl_pct'],
        'amount': pos['amount'],
        'pnl_dollars': pnl_dollars,
        'capital_after': capital,
    })

total_profit = capital - starting_capital
total_return = (capital / starting_capital - 1) * 100
trades_taken = len(trade_log)
wins_taken = sum(1 for t in trade_log if t['pnl_pct'] > 0)
losses_taken = sum(1 for t in trade_log if t['pnl_pct'] <= 0)

print(f"\n  Starting capital: ${starting_capital:,.2f}")
print(f"  Final capital: ${capital:,.2f}")
print(f"  Total profit: ${total_profit:,.2f}")
print(f"  Total return: {total_return:+.1f}%")
print(f"  Trades taken: {trades_taken} (out of {n_trades} available)")
print(f"  Win rate: {wins_taken}/{trades_taken} = {wins_taken/trades_taken*100:.1f}%" if trades_taken > 0 else "  No trades")
print(f"  Avg profit per trade: ${total_profit/trades_taken:.2f}" if trades_taken > 0 else "")

# --- Scenario 3: Max 5 concurrent positions ---
print("\n" + "=" * 70)
print("SCENARIO 3: $1,000, max 5 concurrent, compounding")
print("=" * 70)

capital = starting_capital
max_positions = 5
position_size_pct = 1.0 / max_positions  # 20% each
open_positions = []
trade_log5 = []

for _, trade in one_year.iterrows():
    still_open = []
    for pos in open_positions:
        if pos['exit_date'] <= trade['entry_date']:
            pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
            capital += pnl_dollars
            trade_log5.append({
                'pattern': pos['pattern'],
                'pnl_pct': pos['pnl_pct'],
                'pnl_dollars': pnl_dollars,
                'capital_after': capital,
            })
        else:
            still_open.append(pos)
    open_positions = still_open

    if len(open_positions) < max_positions:
        amount = capital * position_size_pct
        open_positions.append({
            'symbol': trade['symbol'],
            'pattern': trade['pattern'],
            'entry_date': trade['entry_date'],
            'exit_date': pd.to_datetime(trade['exit_date'], utc=True),
            'pnl_pct': trade['pnl_pct'],
            'amount': amount,
        })

for pos in open_positions:
    pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
    capital += pnl_dollars
    trade_log5.append({
        'pattern': pos['pattern'],
        'pnl_pct': pos['pnl_pct'],
        'pnl_dollars': pnl_dollars,
        'capital_after': capital,
    })

total_profit5 = capital - starting_capital
total_return5 = (capital / starting_capital - 1) * 100
trades5 = len(trade_log5)
wins5 = sum(1 for t in trade_log5 if t['pnl_pct'] > 0)

print(f"\n  Starting capital: ${starting_capital:,.2f}")
print(f"  Final capital: ${capital:,.2f}")
print(f"  Total profit: ${total_profit5:,.2f}")
print(f"  Total return: {total_return5:+.1f}%")
print(f"  Trades taken: {trades5} (out of {n_trades} available)")
print(f"  Win rate: {wins5}/{trades5} = {wins5/trades5*100:.1f}%" if trades5 > 0 else "  No trades")

# --- Scenario 4: Only TOP patterns (drop losers) ---
print("\n" + "=" * 70)
print("SCENARIO 4: $1,000, max 3 concurrent, ONLY winning patterns")
print("=" * 70)

# Keep only profitable patterns
winning_patterns = ['Falling Wedge', 'Double Top Breakout', 'Channel Breakout',
                    'Inverse Head & Shoulders', 'Double Bottom', 'Ascending Triangle',
                    'Cup & Handle (Weekly)']
# Drop: Rectangle, C&H Daily, Symmetrical Triangle (marginal)
filtered = one_year[one_year['pattern'].isin(winning_patterns)].copy()

capital = starting_capital
max_positions = 3
position_size_pct = 1.0 / max_positions
open_positions = []
trade_log_top = []

for _, trade in filtered.iterrows():
    still_open = []
    for pos in open_positions:
        if pos['exit_date'] <= trade['entry_date']:
            pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
            capital += pnl_dollars
            trade_log_top.append({
                'pattern': pos['pattern'],
                'pnl_pct': pos['pnl_pct'],
                'pnl_dollars': pnl_dollars,
            })
        else:
            still_open.append(pos)
    open_positions = still_open

    if len(open_positions) < max_positions:
        amount = capital * position_size_pct
        open_positions.append({
            'symbol': trade['symbol'],
            'pattern': trade['pattern'],
            'entry_date': trade['entry_date'],
            'exit_date': pd.to_datetime(trade['exit_date'], utc=True),
            'pnl_pct': trade['pnl_pct'],
            'amount': amount,
        })

for pos in open_positions:
    pnl_dollars = pos['amount'] * pos['pnl_pct'] / 100
    capital += pnl_dollars
    trade_log_top.append({
        'pattern': pos['pattern'],
        'pnl_pct': pos['pnl_pct'],
        'pnl_dollars': pnl_dollars,
    })

total_profit_top = capital - starting_capital
total_return_top = (capital / starting_capital - 1) * 100
trades_top = len(trade_log_top)
wins_top = sum(1 for t in trade_log_top if t['pnl_pct'] > 0)

print(f"\n  Patterns used: {winning_patterns}")
print(f"  Starting capital: ${starting_capital:,.2f}")
print(f"  Final capital: ${capital:,.2f}")
print(f"  Total profit: ${total_profit_top:,.2f}")
print(f"  Total return: {total_return_top:+.1f}%")
print(f"  Trades taken: {trades_top}")
print(f"  Win rate: {wins_top}/{trades_top} = {wins_top/trades_top*100:.1f}%" if trades_top > 0 else "  No trades")

# --- Pattern breakdown for 1 year ---
print("\n" + "=" * 70)
print("PATTERN BREAKDOWN (1 year only)")
print("=" * 70)
for pattern in one_year['pattern'].value_counts().index:
    subset = one_year[one_year['pattern'] == pattern]
    n = len(subset)
    w = (subset['pnl_pct'] > 0).sum()
    exp = subset['pnl_pct'].mean()
    print(f"  {pattern:<30} {n:>4} trades | {w/n*100:>5.1f}% WR | {exp:>+6.2f}% exp")

# --- Summary ---
print("\n" + "=" * 70)
print("SUMMARY: $1,000 for 1 year")
print("=" * 70)
print(f"""
  Scenario 1 (all trades, unlimited capital):  {total_pct:+.1f}% (theoretical max)
  Scenario 2 (max 3 positions, compounding):    {total_return:+.1f}% -> ${starting_capital + total_profit:,.2f}
  Scenario 3 (max 5 positions, compounding):    {total_return5:+.1f}% -> ${starting_capital + total_profit5:,.2f}
  Scenario 4 (top patterns only, max 3):        {total_return_top:+.1f}% -> ${starting_capital + total_profit_top:,.2f}

  NOTE: These are BACKTEST results (no slippage, no fees).
  Real-world: subtract ~1-2% per trade for fees + slippage.
  Survivorship bias: S&P 500 only includes current members.
""")
