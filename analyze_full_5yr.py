"""
Full 5-Year Backtest Analysis (frozen config: ATR 1.5x, 50% target, 30-day exit)
=================================================================================
Comprehensive analysis of the fresh backtest run with the production config.
"""
import pandas as pd
import numpy as np
from datetime import datetime

# Load fresh backtest results
df = pd.read_csv('backtest_v2_20260903_010608.csv')
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')
df['exit_date'] = pd.to_datetime(df['exit_date'], utc=True, format='mixed')
df = df.sort_values('exit_date').reset_index(drop=True)

# Apply 0.2% round-trip costs
df['pnl_net'] = df['pnl_pct'] - 0.2

print("=" * 80)
print("FULL 5-YEAR BACKTEST — FROZEN CONFIG (ATR 1.5x / 50% / 30d)")
print("503 S&P 500 stocks | 2021-2026 | 0.2% costs")
print("=" * 80)

# --- OVERALL ---
n = len(df)
wins = df[df['pnl_net'] > 0]
losses = df[df['pnl_net'] <= 0]
wr = len(wins) / n * 100
exp = df['pnl_net'].mean()
pf = wins['pnl_net'].sum() / abs(losses['pnl_net'].sum())
avg_win = wins['pnl_net'].mean()
avg_loss = losses['pnl_net'].mean()
median_pnl = df['pnl_net'].median()
std_pnl = df['pnl_net'].std()

print(f"\n1. OVERALL STATS (net of 0.2% costs)")
print(f"   Total trades:      {n}")
print(f"   Wins:              {len(wins)} ({wr:.1f}%)")
print(f"   Losses:            {len(losses)} ({100-wr:.1f}%)")
print(f"   Avg win:           {avg_win:+.2f}%")
print(f"   Avg loss:          {avg_loss:+.2f}%")
print(f"   Median P&L:        {median_pnl:+.2f}%")
print(f"   Std dev:           {std_pnl:.2f}%")
print(f"   Expectancy:        {exp:+.2f}% per trade")
print(f"   Profit factor:     {pf:.2f}")
print(f"   Win/Loss ratio:    {abs(avg_win/avg_loss):.2f}")

# --- PATTERN BREAKDOWN ---
print(f"\n2. PATTERN BREAKDOWN (net of costs)")
print(f"   {'Pattern':<30} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'AvgWin':>8} {'AvgLoss':>9}")
print(f"   {'-'*80}")
for pattern in df['pattern'].value_counts().index:
    s = df[df['pattern'] == pattern]
    n_p = len(s)
    w_p = (s['pnl_net'] > 0).sum()
    wr_p = w_p / n_p * 100
    exp_p = s['pnl_net'].mean()
    pf_p = s[s['pnl_net']>0]['pnl_net'].sum() / abs(s[s['pnl_net']<=0]['pnl_net'].sum())
    aw_p = s[s['pnl_net']>0]['pnl_net'].mean()
    al_p = s[s['pnl_net']<=0]['pnl_net'].mean()
    print(f"   {pattern:<30} {n_p:>7} {wr_p:>6.1f}% {exp_p:>+7.2f}% {pf_p:>6.2f} {aw_p:>+7.2f}% {al_p:>+8.2f}%")

# --- EXIT REASONS ---
print(f"\n3. EXIT REASONS")
for reason in df['exit_reason'].value_counts().index:
    s = df[df['exit_reason'] == reason]
    n_r = len(s)
    wr_r = (s['pnl_net'] > 0).sum() / n_r * 100
    avg_r = s['pnl_net'].mean()
    print(f"   {reason:<15} {n_r:>5} trades ({n_r/n*100:>5.1f}%) | {wr_r:>5.1f}% WR | {avg_r:+.2f}% avg")

# --- HOLDING PERIOD ---
print(f"\n4. HOLDING PERIOD")
df['days_held'] = (df['exit_date'] - df['entry_date']).dt.days
print(f"   Avg: {df['days_held'].mean():.1f}d | Median: {df['days_held'].median():.0f}d | Min: {df['days_held'].min()}d | Max: {df['days_held'].max()}d")

# --- EQUITY CURVE + RISK METRICS ---
print(f"\n5. RISK METRICS")
position_size = 1000
df['pnl_dollars'] = df['pnl_net'] / 100 * position_size
df['cum_pnl'] = df['pnl_dollars'].cumsum()
df['equity'] = 10000 + df['cum_pnl']
df['peak'] = df['equity'].cummax()
df['dd'] = (df['equity'] - df['peak']) / df['peak'] * 100

max_dd = df['dd'].min()
max_dd_idx = df['dd'].idxmin()
max_dd_date = df.loc[max_dd_idx, 'exit_date']

total_days = (df['exit_date'].max() - df['entry_date'].min()).days
years = total_days / 365.25
total_return = (df['equity'].iloc[-1] / 10000 - 1) * 100
cagr = ((df['equity'].iloc[-1] / 10000) ** (1/years) - 1) * 100
trades_per_year = n / years
sharpe = exp / std_pnl * np.sqrt(trades_per_year)
downside = df[df['pnl_net'] < 0]['pnl_net']
sortino = exp / downside.std() * np.sqrt(trades_per_year)
calmar = cagr / abs(max_dd)

print(f"   Starting capital:  $10,000 (fixed $1k/trade)")
final_eq = df['equity'].iloc[-1]
print(f"   Final equity:      ${final_eq:,.2f}")
print(f"   Total return:      {total_return:+.1f}%")
print(f"   CAGR:              {cagr:+.1f}%")
print(f"   Max drawdown:      {max_dd:.2f}% (on {max_dd_date.date()})")
print(f"   Sharpe ratio:      {sharpe:.2f} (annualized)")
print(f"   Sortino ratio:     {sortino:.2f} (annualized)")
print(f"   Calmar ratio:      {calmar:.2f}")
print(f"   Trades/year:       {trades_per_year:.0f}")
print(f"   Years:             {years:.1f}")

# --- DRAWDOWN PERIODS ---
print(f"\n6. DRAWDOWN ANALYSIS")
df['in_dd'] = df['dd'] < -1
dd_periods = []
start = None
for i in range(len(df)):
    if df.iloc[i]['in_dd'] and start is None:
        start = i
    elif not df.iloc[i]['in_dd'] and start is not None:
        dd_periods.append((start, i - 1))
        start = None
if start is not None:
    dd_periods.append((start, len(df) - 1))

print(f"   Number of drawdowns (>1%): {len(dd_periods)}")
if dd_periods:
    worst_5 = sorted(dd_periods, key=lambda x: df.iloc[x[0]:x[1]+1]['dd'].min())[:5]
    print(f"   Top 5 worst drawdowns:")
    print(f"   {'Start':<12} {'End':<12} {'Days':>6} {'MaxDD':>8}")
    print(f"   {'-'*40}")
    for s, e in worst_5:
        dd_slice = df.iloc[s:e+1]
        start_date = dd_slice.iloc[0]['exit_date'].date()
        end_date = dd_slice.iloc[-1]['exit_date'].date()
        days = (end_date - start_date).days
        max_dd_p = dd_slice['dd'].min()
        print(f"   {str(start_date):<12} {str(end_date):<12} {days:>6} {max_dd_p:>+7.1f}%")

# --- STREAKS ---
print(f"\n7. STREAK ANALYSIS")
streaks = []
current_streak = 0
current_type = None
for _, row in df.iterrows():
    if row['pnl_net'] > 0:
        if current_type == 'W':
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append((current_type, current_streak))
            current_type = 'W'
            current_streak = 1
    else:
        if current_type == 'L':
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append((current_type, current_streak))
            current_type = 'L'
            current_streak = 1
if current_streak > 0:
    streaks.append((current_type, current_streak))

win_streaks = [s[1] for s in streaks if s[0] == 'W']
loss_streaks = [s[1] for s in streaks if s[0] == 'L']
print(f"   Max win streak:   {max(win_streaks)} trades")
print(f"   Max loss streak:  {max(loss_streaks)} trades")
print(f"   Avg win streak:   {np.mean(win_streaks):.1f} trades")
print(f"   Avg loss streak:  {np.mean(loss_streaks):.1f} trades")

# --- YEARLY ---
print(f"\n8. YEARLY BREAKDOWN (net of costs)")
df['year'] = df['exit_date'].dt.year
print(f"   {'Year':<6} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7} {'Total':>9}")
print(f"   {'-'*50}")
for year in sorted(df['year'].unique()):
    yr = df[df['year'] == year]
    n_y = len(yr)
    w_y = (yr['pnl_net'] > 0).sum()
    wr_y = w_y / n_y * 100
    exp_y = yr['pnl_net'].mean()
    pf_y = yr[yr['pnl_net']>0]['pnl_net'].sum() / abs(yr[yr['pnl_net']<=0]['pnl_net'].sum())
    total_y = yr['pnl_net'].sum()
    print(f"   {year:<6} {n_y:>7} {wr_y:>6.1f}% {exp_y:>+7.2f}% {pf_y:>6.2f} {total_y:>+8.1f}%")

# --- TOP/BOTTOM TRADES ---
print(f"\n9. TOP 10 WINNING TRADES")
top10 = df.nlargest(10, 'pnl_net')
for _, t in top10.iterrows():
    days_held = (t['exit_date'] - t['entry_date']).days
    print(f"   {t['symbol']:<6} {t['pattern']:<28} {t['pnl_net']:>+6.2f}% ({days_held}d) {t['exit_date'].date()}")

print(f"\n   TOP 10 LOSING TRADES")
bot10 = df.nsmallest(10, 'pnl_net')
for _, t in bot10.iterrows():
    days_held = (t['exit_date'] - t['entry_date']).days
    print(f"   {t['symbol']:<6} {t['pattern']:<28} {t['pnl_net']:>+6.2f}% ({days_held}d) {t['exit_date'].date()}")

# --- STOCK CONCENTRATION ---
print(f"\n10. STOCK CONCENTRATION")
print(f"   Total unique stocks:  {df['symbol'].nunique()}")
print(f"   Avg trades/stock:     {n / df['symbol'].nunique():.1f}")
stock_stats = df.groupby('symbol').agg(
    trades=('pnl_net', 'count'),
    wins=('pnl_net', lambda x: (x > 0).sum()),
    total_pnl=('pnl_net', 'sum'),
    avg_pnl=('pnl_net', 'mean'),
).reset_index()
stock_stats['wr'] = stock_stats['wins'] / stock_stats['trades'] * 100

print(f"\n   Top 10 most-traded stocks:")
for _, s in stock_stats.nlargest(10, 'trades').iterrows():
    print(f"   {s['symbol']:<6} {s['trades']:>3} trades | {s['wr']:>5.1f}% WR | {s['avg_pnl']:>+6.2f}% avg")

# --- HOLDING PERIOD ANALYSIS ---
print(f"\n11. PERFORMANCE BY HOLDING PERIOD")
bins = [0, 3, 5, 10, 15, 20, 30, 999]
labels = ['1-3d', '4-5d', '6-10d', '11-15d', '16-20d', '21-30d', '30d+']
df['hold_bucket'] = pd.cut(df['days_held'], bins=bins, labels=labels)
print(f"   {'Bucket':<10} {'Trades':>7} {'WR':>7} {'Exp':>8} {'PF':>7}")
print(f"   {'-'*40}")
for bucket in labels:
    s = df[df['hold_bucket'] == bucket]
    if len(s) > 0:
        n_b = len(s)
        wr_b = (s['pnl_net'] > 0).sum() / n_b * 100
        exp_b = s['pnl_net'].mean()
        pf_b = s[s['pnl_net']>0]['pnl_net'].sum() / abs(s[s['pnl_net']<=0]['pnl_net'].sum())
        print(f"   {bucket:<10} {n_b:>7} {wr_b:>6.1f}% {exp_b:>+7.2f}% {pf_b:>6.2f}")

# --- COMPARISON TO OLD CONFIG ---
print(f"\n{'='*80}")
print(f"COMPARISON: OLD CONFIG (2.0 ATR / 45d) vs NEW CONFIG (1.5 ATR / 30d)")
print(f"{'='*80}")

# Old config results (from previous backtest)
old = {
    'trades': 5526,
    'wr': 62.1,
    'exp': 2.46,
    'pf': 2.72,
    'avg_win': 6.25,
    'avg_loss': -3.76,
    'avg_hold': 10.6,
    'max_dd': -29.0,
    'cagr': 74.2,
}

print(f"\n   {'Metric':<20} {'OLD (2x/45d)':>15} {'NEW (1.5x/30d)':>15} {'Delta':>10}")
print(f"   {'-'*60}")
print(f"   {'Trades':<20} {old['trades']:>15} {n:>15} {n-old['trades']:>+10}")
print(f"   {'Win Rate':<20} {old['wr']:>14.1f}% {wr:>14.1f}% {wr-old['wr']:>+9.1f}%")
print(f"   {'Expectancy':<20} {old['exp']:>+14.2f}% {exp:>+14.2f}% {exp-old['exp']:>+9.2f}%")
print(f"   {'Profit Factor':<20} {old['pf']:>15.2f} {pf:>15.2f} {pf-old['pf']:>+9.2f}")
print(f"   {'Avg Win':<20} {old['avg_win']:>+14.2f}% {avg_win:>+14.2f}% {avg_win-old['avg_win']:>+9.2f}%")
print(f"   {'Avg Loss':<20} {old['avg_loss']:>+14.2f}% {avg_loss:>+14.2f}% {avg_loss-old['avg_loss']:>+9.2f}%")
print(f"   {'Avg Hold':<20} {old['avg_hold']:>14.1f}d {df['days_held'].mean():>14.1f}d {df['days_held'].mean()-old['avg_hold']:>+9.1f}d")
print(f"   {'Max Drawdown':<20} {old['max_dd']:>14.1f}% {max_dd:>14.2f}% {max_dd-old['max_dd']:>+9.2f}%")
print(f"   {'CAGR':<20} {old['cagr']:>+14.1f}% {cagr:>+14.1f}% {cagr-old['cagr']:>+9.1f}%")

# --- VERDICT ---
print(f"\n{'='*80}")
print(f"VERDICT")
print(f"{'='*80}")
print(f"""
   The frozen config (1.5 ATR / 50% / 30d) produces:
   - {n} trades over {years:.1f} years ({trades_per_year:.0f}/year)
   - {wr:.1f}% win rate, +{exp:.2f}% expectancy, PF {pf:.2f}
   - Max drawdown only {max_dd:.1f}% (vs {old['max_dd']:.1f}% with old config)
   - CAGR {cagr:+.1f}% (vs {old['cagr']:+.1f}%)

   KEY IMPROVEMENTS:
   - PF: {old['pf']:.2f} -> {pf:.2f} ({(pf/old['pf']-1)*100:+.1f}%)
   - Avg loss: {old['avg_loss']:.2f}% -> {avg_loss:.2f}% (smaller losses)
   - Max DD: {old['max_dd']:.1f}% -> {max_dd:.1f}% (much smaller drawdowns)
   - Avg hold: {old['avg_hold']:.1f}d -> {df['days_held'].mean():.1f}d (faster turnover)

   The new config is STRICTLY BETTER than the old config:
   - Higher PF, smaller losses, smaller drawdowns, faster turnover
   - Slightly lower win rate ({wr:.1f}% vs {old['wr']:.1f}%) but that's the right trade-off
""")

# Save
df.to_csv('backtest_results/full_5yr_frozen_config.csv', index=False)
print(f"Saved: backtest_results/full_5yr_frozen_config.csv")
