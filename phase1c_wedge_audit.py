"""
Phase 1C: Falling Wedge Visual Audit (v2)
==========================================
Extract actual wedge geometry from price data to classify quality.
Generate charts for 100 random samples.
"""
import pandas as pd
import numpy as np
import pickle
import os
import random
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("FALLING WEDGE VISUAL AUDIT v2 — 100 RANDOM SAMPLES")
print("=" * 80)

# Load price data
print("Loading price data...")
with open('backtest_cache/all_stocks_5y.pkl', 'rb') as f:
    all_data = pickle.load(f)
print(f"Loaded {len(all_data)} stocks")

# Load trades
df = pd.read_csv('backtest_results/sp500_5yr_cleaned_patterns.csv')
df = df.dropna(subset=['pnl_pct'])
df['entry_date'] = pd.to_datetime(df['entry_date'], utc=True, format='mixed')
wedge_trades = df[df['pattern'] == 'Falling Wedge'].copy()
print(f"Total Falling Wedge trades: {len(wedge_trades)}")

# Import helpers
from patterns.helpers import find_local_extrema

def analyze_wedge_quality(df_slice, window=40):
    """Extract wedge geometry and classify quality."""
    s = df_slice.tail(window).reset_index(drop=True)
    if len(df_slice) < window + 5:
        return None

    highs = s['High'].values
    lows = s['Low'].values
    cmp = float(s['Close'].iloc[-1])

    peaks = find_local_extrema(s['High'], order=3, kind='max')
    troughs = find_local_extrema(s['Low'], order=3, kind='min')

    if len(peaks) < 2 or len(troughs) < 2:
        return None

    # Fit trendlines
    def linfit(points):
        if len(points) < 2:
            return None
        xs = np.array([p[0] for p in points], dtype=float)
        ys = np.array([p[1] for p in points], dtype=float)
        if xs.max() == xs.min():
            return None
        m, c = np.polyfit(xs, ys, 1)
        return float(m), float(c)

    up = linfit(peaks[-4:] if len(peaks) >= 4 else peaks)
    lo = linfit(troughs[-4:] if len(troughs) >= 4 else troughs)
    if up is None or lo is None:
        return None

    up_slope, up_int = up
    lo_slope, lo_int = lo

    # Width at start and end
    start_x = peaks[0][0]
    end_x = len(s) - 1
    width_start = (up_slope * start_x + up_int) - (lo_slope * start_x + lo_int)
    width_end = (up_slope * end_x + up_int) - (lo_slope * end_x + lo_int)

    if width_start <= 0 or width_end <= 0:
        return None

    # Convergence ratio: how much did the wedge narrow?
    convergence_ratio = width_end / width_start  # 0 = fully converged, 1 = no convergence

    # Slopes (both should be negative for falling wedge)
    upper_descending = up_slope < 0
    lower_descending = lo_slope < 0
    converging = lo_slope > up_slope  # lower descends slower than upper

    # Number of touch points
    n_peaks = len(peaks)
    n_troughs = len(troughs)
    n_touch = n_peaks + n_troughs

    # Wedge duration (bars)
    duration = end_x - start_x

    # Price change during wedge (%)
    price_start = (up_slope * start_x + up_int + lo_slope * start_x + lo_int) / 2
    price_end = (up_slope * end_x + up_int + lo_slope * end_x + lo_int) / 2
    price_change_pct = (price_end - price_start) / price_start * 100 if price_start > 0 else 0

    # Classify quality
    # CLEARLY_VALID: tight convergence (< 0.5), both descending, >= 4 touch points
    # PROBABLY_VALID: moderate convergence (< 0.7), both descending, >= 3 touch points
    # BORDERLINE: loose convergence (< 0.9), some issues
    # CLEARLY_INVALID: no convergence or not descending

    score = 0
    if convergence_ratio < 0.3:
        score += 3  # very tight
    elif convergence_ratio < 0.5:
        score += 2  # tight
    elif convergence_ratio < 0.7:
        score += 1  # moderate
    else:
        score += 0  # loose

    if upper_descending:
        score += 1
    if lower_descending:
        score += 1
    if converging:
        score += 1
    if n_touch >= 6:
        score += 1
    elif n_touch >= 4:
        score += 0.5

    if score >= 5:
        classification = 'CLEARLY_VALID'
    elif score >= 3.5:
        classification = 'PROBABLY_VALID'
    elif score >= 2:
        classification = 'BORDERLINE'
    else:
        classification = 'CLEARLY_INVALID'

    return {
        'classification': classification,
        'quality_score': score,
        'convergence_ratio': convergence_ratio,
        'up_slope': up_slope,
        'lo_slope': lo_slope,
        'upper_descending': upper_descending,
        'lower_descending': lower_descending,
        'converging': converging,
        'n_peaks': n_peaks,
        'n_troughs': n_troughs,
        'n_touch': n_touch,
        'duration': duration,
        'width_start': width_start,
        'width_end': width_end,
        'price_change_pct': price_change_pct,
        'peaks': peaks,
        'troughs': troughs,
        'up_line': (up_slope, up_int),
        'lo_line': (lo_slope, lo_int),
        'window': window,
    }


# Random sample 100
random.seed(42)
sample_indices = random.sample(range(len(wedge_trades)), min(100, len(wedge_trades)))
sampled = wedge_trades.iloc[sample_indices].reset_index(drop=True)

os.makedirs('wedge_audit', exist_ok=True)

results = []
t0 = time.time()

for idx, (_, trade) in enumerate(sampled.iterrows()):
    if idx % 20 == 0:
        print(f"  Progress: {idx}/{len(sampled)} [{time.time()-t0:.0f}s]")

    symbol = trade['symbol']
    entry_date = trade['entry_date']

    if symbol not in all_data:
        continue

    df_full = all_data[symbol]['daily']
    df_slice = df_full[df_full.index <= entry_date].copy()
    if len(df_slice) < 80:
        continue

    # Try multiple windows (same as detector)
    best_quality = None
    best_window = None
    for w in [40, 60, 80, 120]:
        q = analyze_wedge_quality(df_slice, w)
        if q and (best_quality is None or q['quality_score'] > best_quality['quality_score']):
            best_quality = q
            best_window = w

    if not best_quality:
        results.append({
            'idx': idx, 'symbol': symbol, 'date': entry_date,
            'detected': False, 'classification': 'NOT_DETECTED',
            'pnl_pct': trade['pnl_pct'],
        })
        continue

    q = best_quality
    window = q['window']

    # Generate chart
    s = df_slice.tail(window).reset_index(drop=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

    # Price
    ax1.plot(s.index, s['Close'], color='white', linewidth=1.5, label='Close')
    ax1.fill_between(s.index, s['Low'], s['High'], alpha=0.1, color='blue')

    # Trendlines
    up_slope, up_int = q['up_line']
    lo_slope, lo_int = q['lo_line']
    x_range = np.array(range(len(s)))
    ax1.plot(x_range, up_slope * x_range + up_int, 'r--', linewidth=1.5, label=f'Upper (slope={up_slope:.4f})')
    ax1.plot(x_range, lo_slope * x_range + lo_int, 'g--', linewidth=1.5, label=f'Lower (slope={lo_slope:.4f})')

    # Mark peaks and troughs
    for p in q['peaks']:
        ax1.scatter(p[0], p[1], color='red', s=30, zorder=5)
    for t in q['troughs']:
        ax1.scatter(t[0], t[1], color='green', s=30, zorder=5)

    conv_pct = (1 - q['convergence_ratio']) * 100
    ax1.set_title(f'{symbol} — Falling Wedge — {q["classification"]}\n'
                  f'Convergence: {conv_pct:.1f}% | Touches: {q["n_touch"]} | '
                  f'Score: {q["quality_score"]}/7 | Window: {window}d',
                  fontsize=10, color='white')
    ax1.legend(loc='upper right', fontsize=7)
    ax1.set_facecolor('#1a1a1a')
    ax1.tick_params(colors='white')

    # Volume
    if 'Volume' in s.columns:
        colors = ['green' if s.iloc[i]['Close'] > s.iloc[i]['Open'] else 'red' for i in range(len(s))]
        ax2.bar(s.index, s['Volume'], color=colors, alpha=0.6)
        ax2.set_facecolor('#1a1a1a')
        ax2.tick_params(colors='white')

    plt.tight_layout()
    chart_path = f'wedge_audit/wedge_{idx:03d}_{symbol}.png'
    plt.savefig(chart_path, dpi=100, facecolor='#1a1a1a')
    plt.close()

    results.append({
        'idx': idx,
        'symbol': symbol,
        'date': entry_date,
        'detected': True,
        'classification': q['classification'],
        'quality_score': q['quality_score'],
        'convergence_ratio': q['convergence_ratio'],
        'convergence_pct': conv_pct,
        'up_slope': q['up_slope'],
        'lo_slope': q['lo_slope'],
        'upper_descending': q['upper_descending'],
        'lower_descending': q['lower_descending'],
        'converging': q['converging'],
        'n_peaks': q['n_peaks'],
        'n_troughs': q['n_troughs'],
        'n_touch': q['n_touch'],
        'duration': q['duration'],
        'price_change_pct': q['price_change_pct'],
        'pnl_pct': trade['pnl_pct'],
        'chart': chart_path,
    })

# Summary
print(f"\n{'='*80}")
print("FALLING WEDGE AUDIT RESULTS")
print(f"{'='*80}")

res_df = pd.DataFrame(results)
res_df.to_csv('wedge_audit/audit_results.csv', index=False)

n_detected = res_df['detected'].sum()
n_total = len(res_df)

print(f"\nTotal sampled: {n_total}")
print(f"Detected (wedge geometry found): {n_detected} ({n_detected/n_total*100:.1f}%)")

if n_detected > 0:
    det = res_df[res_df['detected']].copy()
    print(f"\nClassification breakdown:")
    for cls in ['CLEARLY_VALID', 'PROBABLY_VALID', 'BORDERLINE', 'CLEARLY_INVALID']:
        n_cls = (det['classification'] == cls).sum()
        pct = n_cls / n_detected * 100
        print(f"  {cls:<20} {n_cls:>3} ({pct:>5.1f}%)")

    valid_count = (det['classification'].isin(['CLEARLY_VALID', 'PROBABLY_VALID'])).sum()
    borderline = (det['classification'] == 'BORDERLINE').sum()
    invalid = (det['classification'] == 'CLEARLY_INVALID').sum()

    print(f"\n  Valid (clearly + probably): {valid_count} ({valid_count/n_detected*100:.1f}%)")
    print(f"  Borderline:                {borderline} ({borderline/n_detected*100:.1f}%)")
    print(f"  Invalid:                   {invalid} ({invalid/n_detected*100:.1f}%)")

    # Performance by classification
    print(f"\nPerformance by classification:")
    for cls in ['CLEARLY_VALID', 'PROBABLY_VALID', 'BORDERLINE', 'CLEARLY_INVALID']:
        s = det[det['classification'] == cls]
        if len(s) > 0:
            wr = (s['pnl_pct'] > 0).sum() / len(s) * 100
            avg = s['pnl_pct'].mean()
            print(f"  {cls:<20} {len(s):>3} trades | {wr:.1f}% WR | {avg:+.2f}% avg P&L")

    # Convergence stats
    print(f"\nConvergence stats:")
    print(f"  Mean convergence:   {det['convergence_pct'].mean():.1f}%")
    print(f"  Median convergence: {det['convergence_pct'].median():.1f}%")
    print(f"  Min:                {det['convergence_pct'].min():.1f}%")
    print(f"  Max:                {det['convergence_pct'].max():.1f}%")

    # Touch points
    print(f"\nTouch points:")
    print(f"  Mean:   {det['n_touch'].mean():.1f}")
    print(f"  Median: {det['n_touch'].median():.0f}")
    print(f"  Min:    {det['n_touch'].min()}")
    print(f"  Max:    {det['n_touch'].max()}")

    # Slope stats
    print(f"\nSlope stats:")
    print(f"  Upper slope (should be negative): mean={det['up_slope'].mean():.6f}")
    print(f"  Lower slope (should be negative): mean={det['lo_slope'].mean():.6f}")
    print(f"  Upper descending: {det['upper_descending'].sum()}/{n_detected} ({det['upper_descending'].sum()/n_detected*100:.1f}%)")
    print(f"  Lower descending: {det['lower_descending'].sum()}/{n_detected} ({det['lower_descending'].sum()/n_detected*100:.1f}%)")
    print(f"  Converging: {det['converging'].sum()}/{n_detected} ({det['converging'].sum()/n_detected*100:.1f}%)")

print(f"\nCharts saved to: wedge_audit/")
print(f"Results saved to: wedge_audit/audit_results.csv")
