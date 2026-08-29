"""Analyze Falling Wedge detector quality."""
import pandas as pd
import pickle
import numpy as np
from patterns.wedge import detect_falling_wedge, _detect_one, _linfit
from patterns.helpers import find_local_extrema

with open('backtest_cache/all_stocks_5y.pkl', 'rb') as f:
    all_data = pickle.load(f)

audit = pd.read_csv('wedge_audit/audit_summary.csv')
print('AUDIT SAMPLE (50 random Falling Wedge trades):')
wins = audit['win'].sum()
losses = (~audit['win']).sum()
print(f'  Wins: {wins} | Losses: {losses}')
print(f'  Avg P&L: {audit["pnl"].mean():.2f}%')
print()

# Which window size is most commonly matched?
window_counts = {40: 0, 60: 0, 80: 0, 120: 0}
convergence_ratios = []

for idx, row in audit.iterrows():
    symbol = row['symbol']
    if symbol not in all_data:
        continue
    df_full = all_data[symbol]['daily']
    entry_date = pd.to_datetime(row['date'], utc=True)
    df_slice = df_full[df_full.index <= entry_date].copy()

    for w in [40, 60, 80, 120]:
        r = _detect_one(df_slice, w, 2.0, 0.08, 0.5, 1.0)
        if r:
            window_counts[w] += 1
            # Calculate convergence
            s = df_slice.tail(w).reset_index(drop=True)
            peaks = find_local_extrema(s['High'], order=3, kind='max')
            troughs = find_local_extrema(s['Low'], order=3, kind='min')
            if len(peaks) >= 2 and len(troughs) >= 2:
                up = _linfit(peaks[-4:] if len(peaks) >= 4 else peaks)
                lo = _linfit(troughs[-4:] if len(troughs) >= 4 else troughs)
                if up and lo:
                    up_slope, up_int = up
                    lo_slope, lo_int = lo
                    end_x = len(s) - 1
                    start_x = peaks[0][0]
                    ws = (up_slope * start_x + up_int) - (lo_slope * start_x + lo_int)
                    we = (up_slope * end_x + up_int) - (lo_slope * end_x + lo_int)
                    if ws > 0:
                        convergence_ratios.append(we / ws)
            break

print('Window size distribution (first match):')
for w, c in window_counts.items():
    print(f'  {w} bars: {c} detections')

print()
print('Convergence (width_end / width_start):')
conv = np.array(convergence_ratios)
print(f'  Mean:   {conv.mean():.2f}')
print(f'  Median: {np.median(conv):.2f}')
print(f'  Min:    {conv.min():.2f}')
print(f'  Max:    {conv.max():.2f}')
tight = (conv < 0.3).sum()
good = ((conv >= 0.3) & (conv < 0.6)).sum()
loose = ((conv >= 0.6) & (conv < 0.8)).sum()
vloose = (conv >= 0.8).sum()
total = len(conv)
print(f'  <0.3 (very tight):  {tight} ({tight/total*100:.0f}%)')
print(f'  0.3-0.6 (good):     {good} ({good/total*100:.0f}%)')
print(f'  0.6-0.8 (loose):    {loose} ({loose/total*100:.0f}%)')
print(f'  >0.8 (very loose):  {vloose} ({vloose/total*100:.0f}%)')

# Check how many peaks/troughs typically form the wedge
print()
print('Swing point counts (peaks/troughs used):')
peak_counts = []
trough_counts = []
for idx, row in audit.iterrows():
    symbol = row['symbol']
    if symbol not in all_data:
        continue
    df_full = all_data[symbol]['daily']
    entry_date = pd.to_datetime(row['date'], utc=True)
    df_slice = df_full[df_full.index <= entry_date].copy()

    for w in [40, 60, 80, 120]:
        s = df_slice.tail(w).reset_index(drop=True)
        peaks = find_local_extrema(s['High'], order=3, kind='max')
        troughs = find_local_extrema(s['Low'], order=3, kind='min')
        r = _detect_one(df_slice, w, 2.0, 0.08, 0.5, 1.0)
        if r:
            peak_counts.append(len(peaks))
            trough_counts.append(len(troughs))
            break

print(f'  Peaks:   mean={np.mean(peak_counts):.1f} median={np.median(peak_counts):.0f} min={min(peak_counts)} max={max(peak_counts)}')
print(f'  Troughs: mean={np.mean(trough_counts):.1f} median={np.median(trough_counts):.0f} min={min(trough_counts)} max={max(trough_counts)}')

# Verdict
print()
print('VERDICT:')
loose_pct = (loose + vloose) / total * 100
if loose_pct > 40:
    print(f'  {loose_pct:.0f}% of wedges are loose (convergence > 0.6)')
    print('  RECOMMENDATION: Tighten detector — require convergence < 0.6')
elif loose_pct > 25:
    print(f'  {loose_pct:.0f}% of wedges are loose (convergence > 0.6)')
    print('  RECOMMENDATION: Consider tightening — add convergence filter')
else:
    print(f'  Only {loose_pct:.0f}% of wedges are loose (convergence > 0.6)')
    print('  Detector looks reasonable — most wedges are well-formed')
