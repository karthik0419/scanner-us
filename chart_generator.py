"""
chart_generator.py - Generate annotated charts for scanner picks

Creates professional chart images showing:
- Price action (candlesticks)
- Pattern overlay (cup, handle, double bottom)
- Entry, stop loss, targets marked
- Volume bars
- Sector rotation status

Usage:
  python chart_generator.py AAPL
  python chart_generator.py --batch results_us_2026-08-29.csv --top 10
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import argparse
import os

# Chart styling
plt.style.use('dark_background')
COLORS = {
    'entry': '#00ff00',      # Green
    'stop': '#ff0000',       # Red
    'target1': '#00ffff',    # Cyan
    'target2': '#ffff00',    # Yellow
    'pattern': '#ffffff',    # White
    'volume_up': '#00ff0088', # Transparent green
    'volume_down': '#ff000088', # Transparent red
}


def create_chart(symbol, pattern_data=None, save_path=None):
    """
    Create annotated chart for a stock
    
    Args:
        symbol: Stock ticker
        pattern_data: Dict with pattern info (from scanner)
        save_path: Where to save image (default: charts/{symbol}.png)
    """
    
    # Fetch data (6 months for context)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='6mo', interval='1d')
    
    if df.empty:
        print(f"No data for {symbol}")
        return None
    
    # Create figure with 2 subplots (price + volume)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), 
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     facecolor='#0a0a0a')
    
    # Plot candlesticks (simplified as OHLC bars for speed)
    for i in range(len(df)):
        date = df.index[i]
        open_price = df['Open'].iloc[i]
        high = df['High'].iloc[i]
        low = df['Low'].iloc[i]
        close = df['Close'].iloc[i]
        
        color = '#00ff00' if close >= open_price else '#ff0000'
        
        # High-low line
        ax1.plot([i, i], [low, high], color=color, linewidth=0.5, alpha=0.3)
        
        # Body
        height = abs(close - open_price)
        bottom = min(open_price, close)
        rect = Rectangle((i-0.3, bottom), 0.6, height, 
                         facecolor=color, edgecolor=color, alpha=0.8)
        ax1.add_patch(rect)
    
    # Plot close price line
    ax1.plot(range(len(df)), df['Close'], color='#ffffff', linewidth=1, alpha=0.5)
    
    # Add pattern annotations if provided
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
        sector = pattern_data.get('sector', 'Unknown')
        
        # Horizontal lines for entry/stop/targets
        ax1.axhline(entry, color=COLORS['entry'], linestyle='--', linewidth=1.5, 
                   label=f'Entry: ${entry:.2f}', alpha=0.8)
        ax1.axhline(stop, color=COLORS['stop'], linestyle='--', linewidth=1.5,
                   label=f'Stop: ${stop:.2f} ({risk:.1f}%)', alpha=0.8)
        ax1.axhline(t1, color=COLORS['target1'], linestyle='--', linewidth=1,
                   label=f'T1: ${t1:.2f}', alpha=0.6)
        ax1.axhline(t2, color=COLORS['target2'], linestyle='--', linewidth=1,
                   label=f'T2: ${t2:.2f}', alpha=0.4)
        
        # Current price marker
        ax1.scatter([len(df)-1], [cmp], color='#ffffff', s=100, zorder=5,
                   edgecolors='#ffff00', linewidths=2)
        
        # Title with pattern info
        ax1.set_title(f'{symbol} - {pattern_name} ({status})\n'
                     f'Sector: {sector} | R:R {rr:.1f}x | Risk {risk:.1f}%',
                     fontsize=14, fontweight='bold', color='#ffffff', pad=10)
    else:
        ax1.set_title(f'{symbol} - 6 Month Chart', fontsize=14, fontweight='bold')
    
    # Format price axis
    ax1.set_ylabel('Price ($)', fontsize=12, color='#aaaaaa')
    ax1.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.8)
    ax1.set_xlim(-1, len(df))
    
    # Remove x-axis labels (dates on bottom plot only)
    ax1.set_xticks([])
    
    # Volume bars
    colors_vol = [COLORS['volume_up'] if df['Close'].iloc[i] >= df['Open'].iloc[i] 
                  else COLORS['volume_down'] for i in range(len(df))]
    ax2.bar(range(len(df)), df['Volume'], color=colors_vol, width=0.8)
    
    ax2.set_ylabel('Volume', fontsize=10, color='#aaaaaa')
    ax2.set_xlabel('Date', fontsize=10, color='#aaaaaa')
    ax2.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
    ax2.set_xlim(-1, len(df))
    
    # Date labels (show ~10 dates)
    step = max(1, len(df) // 10)
    xticks = range(0, len(df), step)
    xticklabels = [df.index[i].strftime('%m/%d') for i in xticks]
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xticklabels, rotation=45, ha='right', fontsize=8)
    
    # Tight layout
    plt.tight_layout()
    
    # Save
    if save_path is None:
        os.makedirs('charts', exist_ok=True)
        save_path = f'charts/{symbol}_{datetime.now().strftime("%Y%m%d")}.png'
    
    plt.savefig(save_path, dpi=150, facecolor='#0a0a0a', 
                edgecolor='none', bbox_inches='tight')
    print(f"[OK] Saved chart: {save_path}")
    
    plt.close()
    return save_path


def batch_generate(csv_file, top_n=10):
    """Generate charts for top N picks from CSV"""
    
    df = pd.read_csv(csv_file)
    
    # Take top N by score
    df = df.sort_values('score', ascending=False).head(top_n)
    
    print(f"Generating charts for top {len(df)} picks...")
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
            'sector': row['sector'],
        }
        
        create_chart(row['symbol'], pattern_data)
    
    print()
    print(f"[OK] Generated {len(df)} charts in charts/ folder")


def main():
    parser = argparse.ArgumentParser(description='Generate stock charts')
    parser.add_argument('symbol', nargs='?', help='Stock symbol (e.g. AAPL)')
    parser.add_argument('--batch', help='CSV file from scanner')
    parser.add_argument('--top', type=int, default=10, help='Top N picks')
    args = parser.parse_args()
    
    if args.batch:
        batch_generate(args.batch, args.top)
    elif args.symbol:
        # Single chart (fetch pattern data from scanner)
        from scanner_us import scan_stock
        results = scan_stock(args.symbol)
        
        if results:
            # Take highest scoring pattern
            best = max(results, key=lambda x: x['score'])
            create_chart(args.symbol, best)
        else:
            print(f"No patterns found for {args.symbol}")
            create_chart(args.symbol)  # Chart without annotations
    else:
        print("Usage:")
        print("  python chart_generator.py AAPL")
        print("  python chart_generator.py --batch results_us_2026-08-29.csv --top 10")


if __name__ == '__main__':
    main()
