"""Analyze backtest trades by pattern (breaks out C&H Weekly separately)."""
import pandas as pd
import sys

def analyze(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} trades from {csv_path}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nPatterns found: {df['pattern'].value_counts().to_dict()}")
    print()

    print(f"{'Pattern':<30} | {'Trades':>6} | {'Win%':>6} | {'Exp%':>7} | {'PF':>5} | {'AvgWin%':>8} | {'AvgLoss%':>9}")
    print("-" * 95)

    for p in sorted(df['pattern'].unique()):
        sub = df[df['pattern'] == p].copy()
        n = len(sub)
        if n == 0:
            continue
        wins = sub[sub['pnl_pct'] > 0]
        losses = sub[sub['pnl_pct'] <= 0]
        wr = len(wins) / n * 100
        exp = sub['pnl_pct'].mean()
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        pf = wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum()) if len(losses) > 0 and losses['pnl_pct'].sum() != 0 else float('inf')
        print(f"{p:<30} | {n:>6} | {wr:>5.1f}% | {exp:>+6.2f}% | {pf:>5.2f} | {avg_win:>+7.2f}% | {avg_loss:>+8.2f}%")

    print()
    # Summary by exit reason
    if 'exit_reason' in df.columns:
        print("Exit reasons:")
        for r in df['exit_reason'].value_counts().index:
            sub = df[df['exit_reason'] == r]
            print(f"  {r:<15} {len(sub):>4} trades | avg {sub['pnl_pct'].mean():+.2f}%")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'backtest_results/sp500_5yr_274trades.csv'
    analyze(path)
