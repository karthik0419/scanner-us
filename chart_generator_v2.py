"""
Chart Generator v2 - With Pattern Overlay

Improvements:
1. Uses 1 year of data (same as scanner)
2. Draws actual pattern (cup, handle, double bottom shapes)
3. Highlights pattern region
4. Shows current price vs entry clearly
5. Better annotations
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from datetime import datetime
import argparse
import os
import numpy as np

plt.style.use('dark_background')

def create_chart_v2(symbol, pattern_data=None, save_path=None):
    """
    Create annotated chart with pattern overlay
    """
    
    # Fetch 1 year of data (same as scanner)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='1y', interval='1d', auto_adjust=True)
    
    if df.empty:
        print(f"No data for {symbol}")
        return None
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), 
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     facecolor='#0a0a0a')
    
    # Plot price line (simpler than candlesticks for pattern visibility)
    dates = range(len(df))
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    ax1.plot(dates, closes, color='#ffffff', linewidth=1.5, alpha=0.9, label='Close')
    ax1.fill_between(dates, lows, highs, color='#444444', alpha=0.2)
    
    # Add pattern overlay if provided
    if pattern_data:
        entry = pattern_data['entry']
        stop = pattern_data['stop_loss']
        t1 = pattern_data['target_1']
        t2 = pattern_data['target_2']
        cmp = pattern_data['cmp']
        pattern_name = pattern_data['pattern']
        status = pattern_data['status']
        rr = pattern_data['rr']
        risk = pattern_data['risk_pct']
        dist = pattern_data['dist_to_breakout_pct']
        
        # Detect and highlight pattern region
        if 'Double Bottom' in pattern_name:
            # Find the two bottoms (local minima in last 60 bars)
            lookback = min(60, len(df))
            window = df.iloc[-lookback:]
            
            # Find local minima
            lows_series = window['Low']
            minima_indices = []
            for i in range(5, len(lows_series)-5):
                if lows_series.iloc[i] == lows_series.iloc[i-5:i+6].min():
                    minima_indices.append(len(df) - lookback + i)
            
            if len(minima_indices) >= 2:
                # Highlight pattern region (between first bottom and current)
                pattern_start = minima_indices[-2]
                pattern_end = len(df) - 1
                ax1.axvspan(pattern_start, pattern_end, alpha=0.15, color='yellow', 
                           label='Pattern Region')
                
                # Mark the two bottoms
                for idx in minima_indices[-2:]:
                    ax1.scatter([idx], [df['Low'].iloc[idx]], color='#ff00ff', 
                               s=200, marker='v', zorder=5, edgecolors='white', linewidths=2)
                
                # Mark the peak (entry level) between bottoms
                peak_window = df.iloc[minima_indices[-2]:minima_indices[-1]]
                if not peak_window.empty:
                    peak_idx = peak_window['High'].idxmax()
                    peak_pos = df.index.get_loc(peak_idx)
                    ax1.scatter([peak_pos], [df['High'].iloc[peak_pos]], 
                               color='#00ff00', s=200, marker='^', zorder=5, 
                               edgecolors='white', linewidths=2,
                               label='Peak (Entry Level)')
        
        elif 'Cup & Handle' in pattern_name:
            # Highlight cup & handle region
            if 'Weekly' in pattern_name:
                cup_bars = 30
            elif 'Monthly' in pattern_name:
                cup_bars = 24
            else:  # Daily
                cup_bars = 30
            
            pattern_start = max(0, len(df) - cup_bars - 10)
            pattern_end = len(df) - 1
            ax1.axvspan(pattern_start, pattern_end, alpha=0.15, color='cyan',
                       label='Cup & Handle Region')
        
        # Entry/Stop/Target lines
        ax1.axhline(entry, color='#00ff00', linestyle='--', linewidth=2, 
                   label=f'Entry: ${entry:.2f}', alpha=0.9, zorder=3)
        ax1.axhline(stop, color='#ff0000', linestyle='--', linewidth=2,
                   label=f'Stop: ${stop:.2f}', alpha=0.9, zorder=3)
        ax1.axhline(t1, color='#00ffff', linestyle=':', linewidth=1.5,
                   label=f'T1: ${t1:.2f}', alpha=0.7, zorder=3)
        ax1.axhline(t2, color='#ffff00', linestyle=':', linewidth=1.5,
                   label=f'T2: ${t2:.2f}', alpha=0.5, zorder=3)
        
        # Current price marker + annotation
        curr_idx = len(df) - 1
        ax1.scatter([curr_idx], [cmp], color='#ffffff', s=300, zorder=6,
                   edgecolors='#ffff00', linewidths=3, marker='o')
        
        # Add arrow showing distance to entry
        if status == 'NEAR':
            mid_idx = int(len(df) * 0.85)  # Position annotation at 85% of chart
            ax1.annotate('', xy=(mid_idx, entry), xytext=(mid_idx, cmp),
                        arrowprops=dict(arrowstyle='<->', color='yellow', lw=2))
            ax1.text(mid_idx + 5, (entry + cmp) / 2, 
                    f'{dist:.1f}% to breakout', 
                    color='yellow', fontsize=11, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.7))
        
        # Title with detailed info
        title_color = '#00ff00' if status == 'BREAKOUT' else '#ffff00' if status == 'NEAR' else '#ff8800'
        ax1.set_title(f'{symbol} - {pattern_name} [{status}]\n'
                     f'Current: ${cmp:.2f} | Entry: ${entry:.2f} | Stop: ${stop:.2f} ({risk:.1f}% risk)\n'
                     f'Targets: T1 ${t1:.2f} | T2 ${t2:.2f} | R:R {rr:.1f}x',
                     fontsize=13, fontweight='bold', color=title_color, pad=15)
    else:
        ax1.set_title(f'{symbol} - 1 Year Chart', fontsize=14, fontweight='bold')
    
    # Format price axis
    ax1.set_ylabel('Price ($)', fontsize=12, color='#cccccc')
    ax1.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.9, facecolor='#1a1a1a')
    ax1.set_xlim(-2, len(df) + 2)
    ax1.set_xticks([])
    
    # Volume bars
    colors_vol = ['#00ff0040' if df['Close'].iloc[i] >= df['Open'].iloc[i] 
                  else '#ff000040' for i in range(len(df))]
    ax2.bar(dates, df['Volume'], color=colors_vol, width=0.9)
    
    ax2.set_ylabel('Volume', fontsize=10, color='#cccccc')
    ax2.set_xlabel('Date', fontsize=10, color='#cccccc')
    ax2.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
    ax2.set_xlim(-2, len(df) + 2)
    
    # Date labels
    step = max(1, len(df) // 12)
    xticks = range(0, len(df), step)
    xticklabels = [df.index[i].strftime('%b %d') for i in xticks]
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xticklabels, rotation=45, ha='right', fontsize=9)
    
    plt.tight_layout()
    
    # Save
    if save_path is None:
        os.makedirs('charts_v2', exist_ok=True)
        save_path = f'charts_v2/{symbol}_{datetime.now().strftime("%Y%m%d")}.png'
    
    plt.savefig(save_path, dpi=150, facecolor='#0a0a0a', 
                edgecolor='none', bbox_inches='tight')
    print(f"[OK] Saved: {save_path}")
    
    plt.close()
    return save_path


def batch_generate_v2(csv_file, top_n=10):
    """Generate v2 charts for top N picks"""
    
    df = pd.read_csv(csv_file)
    df = df.sort_values('score', ascending=False).head(top_n)
    
    print(f"Generating v2 charts for top {len(df)} picks...")
    print()
    
    for idx, row in df.iterrows():
        pattern_data = {
            'pattern': row['pattern'],
            'status': row['status'],
            'entry': row['entry'],
            'stop_loss': row['stop_loss'],
            'target_1': row['target_1'],
            'target_2': row['target_2'],
            'cmp': row['cmp'],
            'rr': row['rr'],
            'risk_pct': row['risk_pct'],
            'dist_to_breakout_pct': row['dist_to_breakout_pct'],
        }
        
        create_chart_v2(row['symbol'], pattern_data)
    
    print()
    print(f"[OK] Generated {len(df)} charts in charts_v2/ folder")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbol', nargs='?', help='Stock symbol')
    parser.add_argument('--batch', help='CSV file')
    parser.add_argument('--top', type=int, default=10, help='Top N')
    args = parser.parse_args()
    
    if args.batch:
        batch_generate_v2(args.batch, args.top)
    elif args.symbol:
        from scanner_us import scan_stock
        results = scan_stock(args.symbol)
        
        if results:
            best = max(results, key=lambda x: x['score'])
            create_chart_v2(args.symbol, best)
        else:
            print(f"No patterns for {args.symbol}")
            create_chart_v2(args.symbol)
    else:
        print("Usage:")
        print("  python chart_generator_v2.py AFL")
        print("  python chart_generator_v2.py --batch results_us_2026-08-29.csv --top 10")


if __name__ == '__main__':
    main()
