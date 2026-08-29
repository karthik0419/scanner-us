"""
STEP 1: Data Integrity Verification
Verify that WR, avg win/loss, expectancy, PF all reconcile from raw trade data.
Also check for duplicate/overlapping trades.
"""
import pandas as pd
import numpy as np
from datetime import timedelta

df = pd.read_csv('backtest_results/sp500_5yr_all_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')
df['exit_date'] = pd.to_datetime(df['exit_date'], utc=True, format='mixed')

print("=" * 80)
print("STEP 1: DATA INTEGRITY VERIFICATION")
print("=" * 80)

# --- Basic reconciliation ---
n = len(df)
wins = df[df['pnl_pct'] > 0]
losses = df[df['pnl_pct'] <= 0]
time_exits = df[df['exit_reason'] == 'TIME_EXIT']

# Some "wins" might be TIME_EXIT with positive pnl
# Some "losses" might be TIME_EXIT with negative pnl
# Let's be precise:
win_trades = df[df['pnl_pct'] > 0]
loss_trades = df[df['pnl_pct'] <= 0]

n_wins = len(win_trades)
n_losses = len(loss_trades)
wr = n_wins / n * 100
avg_win = win_trades['pnl_pct'].mean()
avg_loss = loss_trades['pnl_pct'].mean()

# Expectancy = (WR * avg_win) - (LR * avg_loss)
# Or simply: mean of all pnl_pct
expectancy_formula = (wr/100 * avg_win) - ((100-wr)/100 * avg_loss)
expectancy_mean = df['pnl_pct'].mean()

# Profit Factor = sum(wins) / abs(sum(losses))
gross_profit = win_trades['pnl_pct'].sum()
gross_loss = abs(loss_trades['pnl_pct'].sum())
pf = gross_profit / gross_loss

print(f"\n--- Reconciliation ---")
print(f"  Total trades:          {n}")
print(f"  Wins:                  {n_wins}")
print(f"  Losses:                {n_losses}")
print(f"  Win rate:              {wr:.2f}%")
print(f"  Avg win:               {avg_win:.4f}%")
print(f"  Avg loss:              {avg_loss:.4f}%")
print(f"  Gross profit (sum):    {gross_profit:.2f}%")
print(f"  Gross loss (sum):      {gross_loss:.2f}%")
print(f"")
print(f"  Expectancy (formula):  {expectancy_formula:.4f}%")
print(f"  Expectancy (mean):     {expectancy_mean:.4f}%")
print(f"  Match: {'YES' if abs(expectancy_formula - expectancy_mean) < 0.01 else 'NO'}")
print(f"")
print(f"  Profit factor:         {pf:.4f}")
print(f"  PF check (gross/loss): {gross_profit:.2f} / {gross_loss:.2f} = {pf:.4f}")
print(f"")

# --- Check for duplicates ---
print(f"\n--- Duplicate/Overlap Analysis ---")

# 1. Same stock, same entry date, different patterns
same_stock_same_date = df.groupby(['symbol', 'entry_date']).size()
duplicates = same_stock_same_date[same_stock_same_date > 1]
print(f"  Same stock + same entry date (multiple patterns): {len(duplicates)} cases")
if len(duplicates) > 0:
    print(f"  Example duplicates:")
    for (sym, date), count in duplicates.head(10).items():
        patterns = df[(df['symbol'] == sym) & (df['entry_date'] == date)]['pattern'].tolist()
        print(f"    {sym} on {date.date()}: {count} trades — {patterns}")

# 2. Same stock, overlapping date ranges (entry before previous exit)
print(f"\n  Checking overlapping trades per stock...")
overlap_count = 0
overlap_examples = []
for sym in df['symbol'].unique():
    sym_trades = df[df['symbol'] == sym].sort_values('entry_date')
    for i in range(len(sym_trades) - 1):
        for j in range(i + 1, len(sym_trades)):
            t1 = sym_trades.iloc[i]
            t2 = sym_trades.iloc[j]
            # Overlap if t2 entry < t1 exit
            if t2['entry_date'] < t1['exit_date']:
                overlap_count += 1
                if len(overlap_examples) < 10:
                    overlap_examples.append({
                        'symbol': sym,
                        't1_entry': t1['entry_date'].date(),
                        't1_exit': t1['exit_date'].date(),
                        't1_pattern': t1['pattern'],
                        't2_entry': t2['entry_date'].date(),
                        't2_exit': t2['exit_date'].date(),
                        't2_pattern': t2['pattern'],
                    })
            else:
                break  # t2 is after t1, no need to check further

print(f"  Overlapping trades (same stock, entry before prev exit): {overlap_count}")
if overlap_examples:
    print(f"  Examples:")
    for ex in overlap_examples:
        print(f"    {ex['symbol']}: {ex['t1_pattern']} ({ex['t1_entry']}->{ex['t1_exit']})")
        print(f"             {ex['t2_pattern']} ({ex['t2_entry']}->{ex['t2_exit']})")

# 3. Same stock, entries within 3 days of each other
print(f"\n  Checking entries within 3 days of each other...")
close_entries = 0
for sym in df['symbol'].unique():
    sym_trades = df[df['symbol'] == sym].sort_values('entry_date')
    dates = sym_trades['entry_date'].tolist()
    for i in range(len(dates) - 1):
        delta = (dates[i + 1] - dates[i]).days
        if delta <= 3:
            close_entries += 1

print(f"  Entries within 3 days (same stock): {close_entries}")

# 4. How many UNIQUE (stock, entry_date) combinations?
unique_combos = df[['symbol', 'entry_date']].drop_duplicates()
print(f"\n  Unique (stock, entry_date) combos: {len(unique_combos)}")
print(f"  Total trades:                       {n}")
print(f"  Duplicate trades:                   {n - len(unique_combos)}")

# 5. If we deduplicate (keep best R:R per stock per entry date)
print(f"\n--- After Deduplication (1 trade per stock per entry date) ---")
df_sorted = df.sort_values('pnl_pct', ascending=False)
df_dedup = df_sorted.drop_duplicates(subset=['symbol', 'entry_date'], keep='first')
n_dedup = len(df_dedup)
wins_dedup = df_dedup[df_dedup['pnl_pct'] > 0]
losses_dedup = df_dedup[df_dedup['pnl_pct'] <= 0]
wr_dedup = len(wins_dedup) / n_dedup * 100
avg_win_dedup = wins_dedup['pnl_pct'].mean()
avg_loss_dedup = losses_dedup['pnl_pct'].mean()
exp_dedup = df_dedup['pnl_pct'].mean()
pf_dedup = wins_dedup['pnl_pct'].sum() / abs(losses_dedup['pnl_pct'].sum())

print(f"  Trades after dedup:    {n_dedup} (was {n}, removed {n - n_dedup})")
print(f"  Win rate:              {wr_dedup:.2f}%")
print(f"  Avg win:               {avg_win_dedup:.4f}%")
print(f"  Avg loss:              {avg_loss_dedup:.4f}%")
print(f"  Expectancy:            {exp_dedup:.4f}%")
print(f"  Profit factor:         {pf_dedup:.4f}")

# 6. Further dedup: 1 trade per stock per 14-day window (scan interval)
print(f"\n--- After 14-day cooldown dedup (1 trade per stock per 14 days) ---")
df_dedup2 = df_dedup.sort_values('entry_date').copy()
keep = []
last_trade_date = {}  # symbol -> last entry date kept

for _, row in df_dedup2.iterrows():
    sym = row['symbol']
    if sym in last_trade_date:
        days_since = (row['entry_date'] - last_trade_date[sym]).days
        if days_since < 14:
            continue  # skip, too close to previous trade
    keep.append(row.name)
    last_trade_date[sym] = row['entry_date']

df_dedup2 = df_dedup2.loc[keep]
n_dedup2 = len(df_dedup2)
wins_dedup2 = df_dedup2[df_dedup2['pnl_pct'] > 0]
losses_dedup2 = df_dedup2[df_dedup2['pnl_pct'] <= 0]
wr_dedup2 = len(wins_dedup2) / n_dedup2 * 100 if n_dedup2 > 0 else 0
avg_win_dedup2 = wins_dedup2['pnl_pct'].mean() if len(wins_dedup2) > 0 else 0
avg_loss_dedup2 = losses_dedup2['pnl_pct'].mean() if len(losses_dedup2) > 0 else 0
exp_dedup2 = df_dedup2['pnl_pct'].mean()
pf_dedup2 = wins_dedup2['pnl_pct'].sum() / abs(losses_dedup2['pnl_pct'].sum()) if len(losses_dedup2) > 0 else float('inf')

print(f"  Trades after 14-day cooldown: {n_dedup2} (was {n}, removed {n - n_dedup2})")
print(f"  Win rate:                     {wr_dedup2:.2f}%")
print(f"  Avg win:                      {avg_win_dedup2:.4f}%")
print(f"  Avg loss:                     {avg_loss_dedup2:.4f}%")
print(f"  Expectancy:                   {exp_dedup2:.4f}%")
print(f"  Profit factor:                {pf_dedup2:.4f}")

# Pattern breakdown after dedup
print(f"\n--- Pattern Breakdown After 14-day Cooldown ---")
for pattern in df_dedup2['pattern'].value_counts().index:
    subset = df_dedup2[df_dedup2['pattern'] == pattern]
    n_p = len(subset)
    w_p = (subset['pnl_pct'] > 0).sum()
    exp_p = subset['pnl_pct'].mean()
    pf_p = subset[subset['pnl_pct']>0]['pnl_pct'].sum() / abs(subset[subset['pnl_pct']<=0]['pnl_pct'].sum()) if (subset['pnl_pct']<=0).any() else float('inf')
    print(f"  {pattern:<30} {n_p:>5} trades | {w_p/n_p*100:>5.1f}% WR | {exp_p:>+6.2f}% exp | PF {pf_p:.2f}")

# Save deduped version
df_dedup2.to_csv('backtest_results/sp500_5yr_deduped.csv', index=False)
print(f"\n  Saved deduped trades to: backtest_results/sp500_5yr_deduped.csv")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"  Raw trades:           {n:>6} | WR {wr:.1f}% | Exp {expectancy_mean:.2f}% | PF {pf:.2f}")
print(f"  After entry dedup:    {n_dedup:>6} | WR {wr_dedup:.1f}% | Exp {exp_dedup:.2f}% | PF {pf_dedup:.2f}")
print(f"  After 14-day cooldown:{n_dedup2:>6} | WR {wr_dedup2:.1f}% | Exp {exp_dedup2:.2f}% | PF {pf_dedup2:.2f}")
