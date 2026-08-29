"""
Chart Generator v3 - Clear & Simple Pattern Recognition

Focus: Make the pattern OBVIOUS
- Draw actual pattern outline (cup shape, double bottom shape)
- Minimal clutter
- Clear annotations
- Professional but simple
"""

import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from datetime import datetime
import argparse
import os
import numpy as np
from scipy.interpolate import make_interp_spline

plt.style.use('dark_background')

def create_chart_v3(symbol, pattern_data=None, save_path=None):
    """
    Create SIMPLE chart with CLEAR pattern overlay
    """
    
    # Fetch data
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='1y', interval='1d', auto_adjust=True)
    
    if df.empty:
        print(f"No data for {symbol}")
        return None
    
    # Create figure (larger for clarity)
    fig, ax1 = plt.subplots(1, 1, figsize=(18, 10), facecolor='#0e0e0e')
    
    # Plot price as LINE (simpler than candlesticks)
    dates = range(len(df))
    closes = df['Close'].values
    
    # Main price line - THICK and WHITE
    ax1.plot(dates, closes, color='#ffffff', linewidth=2.5, alpha=0.95, zorder=2)
    
    # Add pattern overlay
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
        
        # DRAW THE PATTERN SHAPE
        if 'Double Bottom' in pattern_name:
            # Find bottoms in last 60 bars
            lookback = min(60, len(df))
            window_closes = closes[-lookback:]
            
            # Find local minima
            minima = []
            for i in range(5, len(window_closes)-5):
                if window_closes[i] <= min(window_closes[i-5:i+5]):
                    minima.append(i)
            
            if len(minima) >= 2:
                # Get last 2 bottoms
                b1_idx = len(df) - lookback + minima[-2]
                b2_idx = len(df) - lookback + minima[-1]
                b1_price = df['Low'].iloc[b1_idx]
                b2_price = df['Low'].iloc[b2_idx]
                
                # Find peak between
                peak_idx = b1_idx + np.argmax(closes[b1_idx:b2_idx])
                peak_price = closes[peak_idx]
                
                # DRAW THE W-SHAPE (Double Bottom)
                # Line from bottom 1 to peak to bottom 2
                w_x = [b1_idx, peak_idx, b2_idx, len(df)-1]
                w_y = [b1_price, peak_price, b2_price, cmp]
                
                ax1.plot(w_x[:3], w_y[:3], color='#00ffff', linewidth=4, 
                        linestyle='-', alpha=0.8, zorder=5, label='Double Bottom Pattern')
                
                # Mark the bottoms with BIG circles
                ax1.scatter([b1_idx, b2_idx], [b1_price, b2_price], 
                           s=400, color='#ff00ff', marker='o', zorder=6,
                           edgecolors='white', linewidths=3, label='Bottoms')
                
                # Mark the peak (entry breakout level)
                ax1.scatter([peak_idx], [peak_price], s=500, color='#00ff00', 
                           marker='*', zorder=6, edgecolors='white', linewidths=3,
                           label='Breakout Level')
                
                # Shade the pattern region
                ax1.axvspan(b1_idx, len(df)-1, alpha=0.08, color='cyan')
        
        elif 'Cup & Handle' in pattern_name:
            # Determine lookback based on timeframe
            if 'Weekly' in pattern_name:
                cup_bars = 30
            elif 'Monthly' in pattern_name:
                cup_bars = 24
            else:
                cup_bars = 30
            
            lookback = min(cup_bars + 10, len(df))
            pattern_start = len(df) - lookback
            
            # Get cup window
            cup_closes = closes[pattern_start:]
            cup_dates = dates[pattern_start:]
            
            # Find left rim, bottom, right rim
            left_third = len(cup_closes) // 3
            right_start = len(cup_closes) - 10
            
            left_rim_idx = pattern_start + np.argmax(cup_closes[:left_third])
            cup_bottom_idx = pattern_start + left_third + np.argmin(cup_closes[left_third:right_start])
            right_rim_idx = pattern_start + right_start + np.argmax(cup_closes[right_start:])
            
            left_rim = closes[left_rim_idx]
            cup_bottom = closes[cup_bottom_idx]
            right_rim = closes[right_rim_idx]
            
            # DRAW THE CUP SHAPE (smooth U-shape)
            cup_x = [left_rim_idx, cup_bottom_idx, right_rim_idx]
            cup_y = [left_rim, cup_bottom, right_rim]
            
            # Interpolate for smooth curve
            if len(cup_x) >= 3:
                x_smooth = np.linspace(cup_x[0], cup_x[-1], 100)
                spl = make_interp_spline(cup_x, cup_y, k=2)
                y_smooth = spl(x_smooth)
                
                ax1.plot(x_smooth, y_smooth, color='#00ffff', linewidth=5, 
                        linestyle='-', alpha=0.9, zorder=5, label='Cup Shape')
            
            # Mark rims and bottom
            ax1.scatter([left_rim_idx, right_rim_idx], [left_rim, right_rim],
                       s=400, color='#00ff00', marker='o', zorder=6,
                       edgecolors='white', linewidths=3, label='Cup Rims')
            ax1.scatter([cup_bottom_idx], [cup_bottom], s=400, color='#ff00ff',
                       marker='v', zorder=6, edgecolors='white', linewidths=3,
                       label='Cup Bottom')
            
            # Shade cup region
            ax1.axvspan(pattern_start, len(df)-1, alpha=0.08, color='cyan')
        
        # CURRENT PRICE - BIG MARKER
        curr_idx = len(df) - 1
        ax1.scatter([curr_idx], [cmp], s=800, color='yellow', marker='D', 
                   zorder=10, edgecolors='white', linewidths=4, label=f'NOW: ${cmp:.2f}')
        
        # Entry, Stop, Targets - THICK LINES with labels ON the line
        # Entry (green)
        ax1.axhline(entry, color='#00ff00', linestyle='--', linewidth=3, 
                   alpha=0.95, zorder=4)
        ax1.text(len(df) * 0.02, entry, f'  ENTRY ${entry:.2f}', 
                color='#00ff00', fontsize=14, fontweight='bold', va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # Stop (red)
        ax1.axhline(stop, color='#ff0000', linestyle='--', linewidth=3, 
                   alpha=0.95, zorder=4)
        ax1.text(len(df) * 0.02, stop, f'  STOP ${stop:.2f} (-{risk:.1f}%)', 
                color='#ff0000', fontsize=14, fontweight='bold', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # Target 1 (cyan)
        ax1.axhline(t1, color='#00ffff', linestyle=':', linewidth=2.5, 
                   alpha=0.85, zorder=4)
        ax1.text(len(df) * 0.98, t1, f'TARGET 1: ${t1:.2f}  ', 
                color='#00ffff', fontsize=13, fontweight='bold', va='bottom',
                ha='right', bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # Target 2 (yellow)
        ax1.axhline(t2, color='#ffff00', linestyle=':', linewidth=2.5, 
                   alpha=0.7, zorder=4)
        ax1.text(len(df) * 0.98, t2, f'TARGET 2: ${t2:.2f}  ', 
                color='#ffff00', fontsize=13, fontweight='bold', va='bottom',
                ha='right', bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # Distance arrow (if NEAR)
        if status == 'NEAR' and dist > 0:
            arrow_x = len(df) * 0.5
            ax1.annotate('', xy=(arrow_x, entry), xytext=(arrow_x, cmp),
                        arrowprops=dict(arrowstyle='<->', color='yellow', lw=4))
            ax1.text(arrow_x + len(df)*0.02, (entry + cmp) / 2, 
                    f'{dist:.1f}%\nTO BREAKOUT', 
                    color='yellow', fontsize=15, fontweight='bold',
                    ha='left', va='center',
                    bbox=dict(boxstyle='round,pad=0.7', facecolor='black', 
                             edgecolor='yellow', linewidth=2, alpha=0.9))
        
        # BIG TITLE
        status_emoji = {'BREAKOUT': '[BREAKING OUT NOW]', 'NEAR': '[APPROACHING BREAKOUT]', 'WATCH': '[WATCHING]'}
        status_color = {'BREAKOUT': '#00ff00', 'NEAR': '#ffff00', 'WATCH': '#ff8800'}
        
        title = f'{symbol}  |  {pattern_name}\n'
        title += f'{status_emoji.get(status, status)}  |  R:R {rr:.1f}x  |  Risk {risk:.1f}%'
        
        ax1.text(0.5, 0.98, title, transform=ax1.transAxes,
                fontsize=18, fontweight='bold', color=status_color.get(status, 'white'),
                ha='center', va='top',
                bbox=dict(boxstyle='round,pad=1', facecolor='#0e0e0e', 
                         edgecolor=status_color.get(status, 'white'), linewidth=3, alpha=0.95))
    
    # Format axes
    ax1.set_ylabel('Price ($)', fontsize=14, color='#cccccc', fontweight='bold')
    ax1.set_xlabel('Time (1 Year)', fontsize=14, color='#cccccc', fontweight='bold')
    ax1.grid(True, alpha=0.15, linestyle=':', linewidth=0.8, color='#555555')
    ax1.set_xlim(-5, len(df) + 5)
    
    # Clean up - remove top/right spines
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#555555')
    ax1.spines['bottom'].set_color('#555555')
    
    # Legend (bottom left, small)
    if pattern_data:
        ax1.legend(loc='lower left', fontsize=10, framealpha=0.9, 
                  facecolor='#1a1a1a', edgecolor='#555555')
    
    # Remove x-axis tick labels (cleaner)
    ax1.set_xticks([])
    
    plt.tight_layout()
    
    # Save
    if save_path is None:
        os.makedirs('charts_v3', exist_ok=True)
        save_path = f'charts_v3/{symbol}_{datetime.now().strftime("%Y%m%d")}.png'
    
    plt.savefig(save_path, dpi=200, facecolor='#0e0e0e', 
                edgecolor='none', bbox_inches='tight')
    print(f"[OK] Saved: {save_path}")
    
    plt.close()
    return save_path


def batch_generate_v3(csv_file, top_n=10):
    """Generate v3 charts"""
    import pandas as pd
    
    df = pd.read_csv(csv_file)
    df = df.sort_values('score', ascending=False).head(top_n)
    
    print(f"Generating v3 charts (CLEAR & SIMPLE) for top {len(df)} picks...")
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
        
        create_chart_v3(row['symbol'], pattern_data)
    
    print()
    print(f"[OK] Generated {len(df)} charts in charts_v3/ folder")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbol', nargs='?', help='Stock symbol')
    parser.add_argument('--batch', help='CSV file')
    parser.add_argument('--top', type=int, default=5, help='Top N')
    args = parser.parse_args()
    
    if args.batch:
        batch_generate_v3(args.batch, args.top)
    elif args.symbol:
        from scanner_us import scan_stock
        results = scan_stock(args.symbol)
        
        if results:
            best = max(results, key=lambda x: x['score'])
            create_chart_v3(args.symbol, best)
        else:
            print(f"No patterns for {args.symbol}")
            create_chart_v3(args.symbol)
    else:
        print("Usage:")
        print("  python chart_generator_v3.py AFL")
        print("  python chart_generator_v3.py --batch results_us_2026-08-29.csv --top 5")


if __name__ == '__main__':
    main()
