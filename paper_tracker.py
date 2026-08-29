"""Paper trade tracker for scanner-us picks.

Tracks live picks from scan results, fetches current prices, and calculates P&L.
Supports NEAR picks (waits for breakout) and BREAKOUT picks (entered immediately).

Usage:
    python paper_tracker.py init                    # init from latest scan CSV
    python paper_tracker.py init --file results_us_2026-08-29.csv
    python paper_tracker.py update                  # fetch prices, update status
    python paper_tracker.py status                  # show all trades
    python paper_tracker.py summary                 # one-line summary
"""
import pandas as pd
import yfinance as yf
import os
import json
import argparse
from datetime import datetime, timedelta

TRACKER_FILE = os.path.join(os.path.dirname(__file__), 'paper_tracker.json')


def init_tracker(csv_file=None):
    """Initialize tracker from scan results CSV."""
    if csv_file is None:
        # Find latest results CSV
        csvs = sorted([f for f in os.listdir(os.path.dirname(__file__))
                       if f.startswith('results_us_') and f.endswith('.csv')])
        if not csvs:
            print("No scan results found. Run a scan first.")
            return
        csv_file = os.path.join(os.path.dirname(__file__), csvs[-1])

    print(f"Loading picks from: {csv_file}")
    df = pd.read_csv(csv_file)

    # Load existing tracker or create new
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            tracker = json.load(f)
        existing_symbols = {t['symbol'] for t in tracker['trades']}
        print(f"  Existing tracker: {len(existing_symbols)} trades")
    else:
        tracker = {'trades': [], 'created': datetime.now().strftime('%Y-%m-%d')}
        existing_symbols = set()

    # Add new picks (skip if already tracking)
    new_count = 0
    for _, row in df.iterrows():
        symbol = row['symbol']
        if symbol in existing_symbols:
            continue

        trade = {
            'symbol': symbol,
            'pattern': row.get('pattern', ''),
            'status_code': row.get('status', ''),
            'entry': float(row.get('entry', 0)),
            'stop_loss': float(row.get('stop_loss', 0)),
            'target_1': float(row.get('target_1', 0)),
            'target_2': float(row.get('target_2', 0)),
            'risk_pct': float(row.get('risk_pct', 0)),
            'rr': float(row.get('rr', 0)),
            'score': float(row.get('score', 0)),
            'mtf_confirmed': bool(row.get('mtf_confirmed', False)),
            'scan_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'WAITING_BREAKOUT' if row.get('status') == 'NEAR' else 'OPEN',
            'entry_date': None if row.get('status') == 'NEAR' else datetime.now().strftime('%Y-%m-%d'),
            'entry_price': None if row.get('status') == 'NEAR' else float(row.get('entry', 0)),
            'exit_date': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl_pct': None,
            'days_held': None,
            'current_price': None,
        }
        tracker['trades'].append(trade)
        new_count += 1

    print(f"  Added {new_count} new picks")
    print(f"  Total trades: {len(tracker['trades'])}")

    with open(TRACKER_FILE, 'w') as f:
        json.dump(tracker, f, indent=2)
    print(f"  Saved to: {TRACKER_FILE}")


def update_tracker():
    """Fetch current prices and update trade status."""
    if not os.path.exists(TRACKER_FILE):
        print("No tracker found. Run 'python paper_tracker.py init' first.")
        return

    with open(TRACKER_FILE, 'r') as f:
        tracker = json.load(f)

    open_trades = [t for t in tracker['trades'] if t['status'] in ('WAITING_BREAKOUT', 'OPEN')]
    if not open_trades:
        print("No open trades to update.")
        return

    print(f"Updating {len(open_trades)} open trades...")

    for trade in open_trades:
        symbol = trade['symbol']
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')
            if hist.empty:
                continue
            hist = hist.dropna(subset=['Close'])
            if hist.empty:
                continue
            current = float(hist['Close'].iloc[-1])
            trade['current_price'] = current

            if trade['status'] == 'WAITING_BREAKOUT':
                # Check if price crossed breakout level
                breakout = trade['entry']
                if current >= breakout:
                    trade['status'] = 'OPEN'
                    trade['entry_date'] = datetime.now().strftime('%Y-%m-%d')
                    trade['entry_price'] = breakout
                    print(f"  [BREAKOUT] {symbol} broke out to ${current:.2f} >= ${breakout:.2f} — entered")
                else:
                    dist = (breakout - current) / current * 100
                    print(f"  [WAITING] {symbol} at ${current:.2f}, breakout at ${breakout:.2f} ({dist:.1f}% away)")

            if trade['status'] == 'OPEN':
                entry = trade['entry_price']
                sl = trade['stop_loss']
                t1 = trade['target_1']
                t2 = trade['target_2']

                if current <= sl:
                    trade['status'] = 'LOSS'
                    trade['exit_date'] = datetime.now().strftime('%Y-%m-%d')
                    trade['exit_price'] = sl
                    trade['exit_reason'] = 'STOP_LOSS'
                    trade['pnl_pct'] = (sl - entry) / entry * 100
                    print(f"  [LOSS] {symbol} hit SL at ${current:.2f} (SL: ${sl:.2f}) — {trade['pnl_pct']:+.1f}%")
                elif current >= t2:
                    trade['status'] = 'WIN_T2'
                    trade['exit_date'] = datetime.now().strftime('%Y-%m-%d')
                    trade['exit_price'] = t2
                    trade['exit_reason'] = 'TARGET_2'
                    trade['pnl_pct'] = (t2 - entry) / entry * 100
                    print(f"  [WIN_T2] {symbol} hit T2 at ${current:.2f} (T2: ${t2:.2f}) — {trade['pnl_pct']:+.1f}%")
                elif current >= t1:
                    if trade.get('t1_hit') is None:
                        trade['t1_hit'] = datetime.now().strftime('%Y-%m-%d')
                        print(f"  [WIN_T1] {symbol} hit T1 at ${current:.2f} (T1: ${t1:.2f}) — holding for T2")
                    else:
                        pnl = (current - entry) / entry * 100
                        print(f"  [OPEN] {symbol} at ${current:.2f} — {pnl:+.1f}% (T1 hit, holding for T2)")
                else:
                    pnl = (current - entry) / entry * 100
                    print(f"  [OPEN] {symbol} at ${current:.2f} — {pnl:+.1f}% (SL: ${sl:.2f}, T1: ${t1:.2f})")

                # Check time exit (45 days)
                if trade['status'] == 'OPEN' and trade.get('entry_date'):
                    entry_date = datetime.strptime(trade['entry_date'], '%Y-%m-%d')
                    days = (datetime.now() - entry_date).days
                    if days >= 45:
                        trade['status'] = 'TIME_EXIT'
                        trade['exit_date'] = datetime.now().strftime('%Y-%m-%d')
                        trade['exit_price'] = current
                        trade['exit_reason'] = 'TIME_EXIT'
                        trade['pnl_pct'] = (current - entry) / entry * 100
                        print(f"  [TIME_EXIT] {symbol} held {days} days — {trade['pnl_pct']:+.1f}%")

        except Exception as e:
            print(f"  [ERROR] {symbol}: {e}")

    with open(TRACKER_FILE, 'w') as f:
        json.dump(tracker, f, indent=2)
    print(f"\nTracker updated. Saved to {TRACKER_FILE}")
    summary(tracker)


def status():
    """Show all trades."""
    if not os.path.exists(TRACKER_FILE):
        print("No tracker found. Run 'python paper_tracker.py init' first.")
        return

    with open(TRACKER_FILE, 'r') as f:
        tracker = json.load(f)

    print(f"\n{'='*100}")
    print(f"PAPER TRACKER — {len(tracker['trades'])} trades (created {tracker.get('created', '?')})")
    print(f"{'='*100}")
    print(f"{'Symbol':<8} {'Pattern':<25} {'Status':<16} {'Entry':>8} {'CMP':>8} {'SL':>8} {'T1':>8} {'PnL%':>7} {'Days':>5}")
    print("-" * 100)

    for t in tracker['trades']:
        sym = t['symbol']
        pat = t.get('pattern', '')[:24]
        status = t['status']
        entry = t.get('entry_price') or t.get('entry', 0)
        cmp = t.get('current_price') or 0
        sl = t.get('stop_loss', 0)
        t1 = t.get('target_1', 0)
        pnl = t.get('pnl_pct')
        days = ''
        if t.get('entry_date') and t.get('exit_date'):
            d1 = datetime.strptime(t['entry_date'], '%Y-%m-%d')
            d2 = datetime.strptime(t['exit_date'], '%Y-%m-%d')
            days = str((d2 - d1).days)
        elif t.get('entry_date'):
            days = str((datetime.now() - datetime.strptime(t['entry_date'], '%Y-%m-%d')).days)

        pnl_str = f"{pnl:+.1f}%" if pnl is not None else "—"
        print(f"{sym:<8} {pat:<25} {status:<16} ${entry:>7.2f} ${cmp:>7.2f} ${sl:>7.2f} ${t1:>7.2f} {pnl_str:>7} {days:>5}")

    print()
    summary(tracker)


def summary(tracker=None):
    """One-line summary."""
    if tracker is None:
        if not os.path.exists(TRACKER_FILE):
            print("No tracker found.")
            return
        with open(TRACKER_FILE, 'r') as f:
            tracker = json.load(f)

    trades = tracker['trades']
    total = len(trades)
    open_count = sum(1 for t in trades if t['status'] in ('OPEN', 'WAITING_BREAKOUT'))
    closed = [t for t in trades if t['pnl_pct'] is not None]
    wins = [t for t in closed if t['pnl_pct'] > 0]
    losses = [t for t in closed if t['pnl_pct'] <= 0]

    wr = len(wins) / len(closed) * 100 if closed else 0
    avg_pnl = sum(t['pnl_pct'] for t in closed) / len(closed) if closed else 0

    print(f"\nSummary: {total} trades | {open_count} open | {len(closed)} closed | "
          f"WR: {wr:.0f}% | Avg PnL: {avg_pnl:+.1f}% | "
          f"Wins: {len(wins)} | Losses: {len(losses)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Paper Trade Tracker')
    parser.add_argument('command', choices=['init', 'update', 'status', 'summary'])
    parser.add_argument('--file', help='Scan results CSV to init from')
    args = parser.parse_args()

    if args.command == 'init':
        init_tracker(args.file)
    elif args.command == 'update':
        update_tracker()
    elif args.command == 'status':
        status()
    elif args.command == 'summary':
        summary()
