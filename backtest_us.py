"""
backtest_us.py - Backtest scanner-us on historical US stock data

Methodology:
1. Scan historical data (every Monday for 2 years)
2. Enter trades when patterns trigger (BREAKOUT status or NEAR→BREAKOUT)
3. Exit at: Target 1, Stop Loss, or 45 days (time exit)
4. Track: Win rate, avg win/loss, expectancy, profit factor, max DD

Usage:
  python backtest_us.py                           # Backtest backbone_us.txt
  python backtest_us.py --stocks sp500.txt        # Backtest S&P 500
  python backtest_us.py --years 3                 # 3 years of data
  python backtest_us.py --capital 10000           # $10k starting capital
"""

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
from scanner_us import scan_stock, get_sector_heat
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class Trade:
    def __init__(self, symbol, pattern, entry_date, entry_price, stop_loss, target_1, target_2):
        self.symbol = symbol
        self.pattern = pattern
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target_1 = target_1
        self.target_2 = target_2
        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_pct = 0.0
        self.days_held = 0
        self.status = 'OPEN'
    
    def close(self, exit_date, exit_price, reason):
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        self.days_held = (exit_date - self.entry_date).days
        self.status = 'CLOSED'
    
    def __repr__(self):
        if self.status == 'OPEN':
            return f"{self.symbol} {self.pattern} OPEN @${self.entry_price:.2f}"
        else:
            return f"{self.symbol} {self.pattern} {self.exit_reason} {self.pnl_pct:+.1f}% ({self.days_held}d)"


def run_backtest(symbols, years=2, capital=10000):
    """Run backtest on given stock list"""
    
    print("=" * 80)
    print("BACKTEST - scanner-us")
    print("=" * 80)
    print(f"Stocks: {len(symbols)}")
    print(f"Period: {years} years")
    print(f"Starting capital: ${capital:,.0f}")
    print("=" * 80)
    print()
    
    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    # Generate scan dates (every Monday)
    scan_dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() == 0:  # Monday
            scan_dates.append(current)
        current += timedelta(days=1)
    
    print(f"Scan dates: {len(scan_dates)} (weekly scans)")
    print()
    
    # Backtest state
    open_trades = []
    closed_trades = []
    equity_curve = [(start_date, capital)]
    current_capital = capital
    
    # Run backtest
    for scan_idx, scan_date in enumerate(scan_dates):
        print(f"[{scan_idx+1}/{len(scan_dates)}] Scanning {scan_date.strftime('%Y-%m-%d')}...", end='\r')
        
        # Close open trades first (check if SL/T1 hit, or 45 days expired)
        for trade in list(open_trades):
            try:
                # Fetch data from entry to now
                ticker = yf.Ticker(trade.symbol)
                df = ticker.history(start=trade.entry_date, end=scan_date + timedelta(days=1))
                
                if df.empty:
                    continue
                
                # Check for stop loss
                if df['Low'].min() <= trade.stop_loss:
                    exit_date = df[df['Low'] <= trade.stop_loss].index[0]
                    trade.close(exit_date, trade.stop_loss, 'LOSS (Stop Hit)')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
                
                # Check for target 1
                if df['High'].max() >= trade.target_1:
                    exit_date = df[df['High'] >= trade.target_1].index[0]
                    trade.close(exit_date, trade.target_1, 'WIN (T1 Hit)')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
                
                # Check for time exit (45 days)
                if (scan_date - trade.entry_date).days >= 45:
                    exit_price = df['Close'].iloc[-1]
                    trade.close(scan_date, exit_price, 'TIME_EXIT (45d)')
                    open_trades.remove(trade)
                    closed_trades.append(trade)
                    continue
            
            except:
                pass
        
        # Scan for new setups
        for symbol in symbols:
            try:
                # Skip if already have open trade in this symbol
                if any(t.symbol == symbol for t in open_trades):
                    continue
                
                # Scan
                results = scan_stock(symbol)
                if not results:
                    continue
                
                # Take highest scoring BREAKOUT setup
                breakouts = [r for r in results if r['status'] == 'BREAKOUT' and r['score'] >= 40]
                if not breakouts:
                    continue
                
                best = max(breakouts, key=lambda x: x['score'])
                
                # Enter trade (next day open)
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=scan_date, end=scan_date + timedelta(days=5))
                if df.empty:
                    continue
                
                entry_date = df.index[0]
                entry_price = df['Open'].iloc[0]
                
                trade = Trade(
                    symbol=symbol,
                    pattern=best['pattern'],
                    entry_date=entry_date,
                    entry_price=entry_price,
                    stop_loss=best['stop_loss'],
                    target_1=best['target_1'],
                    target_2=best['target_2'],
                )
                open_trades.append(trade)
            
            except:
                pass
        
        # Update equity curve
        open_pnl = sum((t.entry_price - t.entry_price) for t in open_trades)  # Unrealized P&L (0 for now, simplification)
        closed_pnl = sum((t.exit_price - t.entry_price) for t in closed_trades)
        current_capital = capital + closed_pnl
        equity_curve.append((scan_date, current_capital))
    
    print()
    print()
    
    # Close any remaining open trades at final price
    for trade in open_trades:
        try:
            ticker = yf.Ticker(trade.symbol)
            df = ticker.history(start=trade.entry_date, end=end_date)
            exit_price = df['Close'].iloc[-1]
            trade.close(end_date, exit_price, 'BACKTEST_END')
            closed_trades.append(trade)
        except:
            pass
    
    # Calculate statistics
    total_trades = len(closed_trades)
    if total_trades == 0:
        print("No trades found. Try increasing the time period or stock universe.")
        return
    
    wins = [t for t in closed_trades if t.pnl_pct > 0]
    losses = [t for t in closed_trades if t.pnl_pct <= 0]
    
    win_rate = len(wins) / total_trades * 100
    avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
    expectancy = (len(wins) * avg_win + len(losses) * avg_loss) / total_trades
    
    total_gains = sum(t.pnl_pct for t in wins) if wins else 0
    total_losses = abs(sum(t.pnl_pct for t in losses)) if losses else 1
    profit_factor = total_gains / total_losses if total_losses > 0 else 0
    
    # Max drawdown
    equity_df = pd.DataFrame(equity_curve, columns=['Date', 'Equity'])
    equity_df['Peak'] = equity_df['Equity'].cummax()
    equity_df['Drawdown'] = (equity_df['Equity'] - equity_df['Peak']) / equity_df['Peak'] * 100
    max_dd = equity_df['Drawdown'].min()
    
    final_capital = equity_curve[-1][1]
    total_return = (final_capital - capital) / capital * 100
    cagr = ((final_capital / capital) ** (1 / years) - 1) * 100
    
    # Print results
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print()
    print(f"Total trades: {total_trades}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg win: {avg_win:+.1f}%")
    print(f"Avg loss: {avg_loss:+.1f}%")
    print(f"Expectancy: {expectancy:+.2f}% per trade")
    print(f"Profit factor: {profit_factor:.2f}")
    print(f"Max drawdown: {max_dd:.1f}%")
    print()
    print(f"Starting capital: ${capital:,.0f}")
    print(f"Final capital: ${final_capital:,.0f}")
    print(f"Total return: {total_return:+.1f}%")
    print(f"CAGR: {cagr:+.1f}%")
    print()
    
    # Pattern breakdown
    pattern_stats = {}
    for trade in closed_trades:
        pattern = trade.pattern
        if pattern not in pattern_stats:
            pattern_stats[pattern] = {'trades': 0, 'wins': 0, 'pnl': []}
        pattern_stats[pattern]['trades'] += 1
        if trade.pnl_pct > 0:
            pattern_stats[pattern]['wins'] += 1
        pattern_stats[pattern]['pnl'].append(trade.pnl_pct)
    
    print("Pattern breakdown:")
    for pattern, stats in sorted(pattern_stats.items(), key=lambda x: len(x[1]['pnl']), reverse=True):
        wr = stats['wins'] / stats['trades'] * 100
        exp = np.mean(stats['pnl'])
        print(f"  {pattern:<30} {stats['trades']:>4} trades | {wr:>5.1f}% WR | {exp:+6.2f}% exp")
    print()
    
    # Sample trades
    print("Sample trades (last 20):")
    for trade in closed_trades[-20:]:
        print(f"  {trade}")
    print()
    
    # Save results
    df = pd.DataFrame([{
        'symbol': t.symbol,
        'pattern': t.pattern,
        'entry_date': t.entry_date,
        'entry_price': t.entry_price,
        'exit_date': t.exit_date,
        'exit_price': t.exit_price,
        'exit_reason': t.exit_reason,
        'pnl_pct': t.pnl_pct,
        'days_held': t.days_held,
    } for t in closed_trades])
    
    output_file = f"backtest_results_us_{datetime.now().strftime('%Y-%m-%d')}.csv"
    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Backtest US Stock Scanner')
    parser.add_argument('--stocks', default='backbone_us.txt', help='Stock list file')
    parser.add_argument('--years', type=int, default=2, help='Years of historical data')
    parser.add_argument('--capital', type=float, default=10000, help='Starting capital ($)')
    args = parser.parse_args()
    
    # Load stock list
    with open(args.stocks, 'r') as f:
        symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    run_backtest(symbols, years=args.years, capital=args.capital)


if __name__ == '__main__':
    main()
