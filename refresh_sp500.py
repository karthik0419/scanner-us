"""
Refresh S&P 500 stock list from Wikipedia.
Updates sp500.txt and sp500_sectors.json with current constituents.

Usage:
    python refresh_sp500.py           # Refresh from Wikipedia
    python refresh_sp500.py --check   # Show what changed (don't write)

Source: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
"""
import requests
import pandas as pd
import json
import os
import argparse
import io
from datetime import datetime

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def fetch_sp500_from_wikipedia():
    """Fetch current S&P 500 constituents from Wikipedia."""
    print("Fetching S&P 500 list from Wikipedia...")

    # Wikipedia blocks default urllib user agent, need a real one
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(WIKI_URL, headers=headers)
    response.raise_for_status()

    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]  # First table is the constituents list

    # Columns: Symbol, Security, GICS Sector, GICS Sub-Industry, Headquarters, Date Added, CIK, Founded
    # Clean up symbol (replace dots with dashes for yfinance compatibility)
    df['Symbol'] = df['Symbol'].str.strip()
    # yfinance uses dashes instead of dots (BRK.B -> BRK-B)
    df['Symbol_yf'] = df['Symbol'].str.replace('.', '-', regex=False)

    print(f"  Found {len(df)} stocks on Wikipedia")
    return df


def load_current_sp500():
    """Load current sp500.txt."""
    path = os.path.join(os.path.dirname(__file__), 'sp500.txt')
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def load_current_sectors():
    """Load current sp500_sectors.json."""
    path = os.path.join(os.path.dirname(__file__), 'sp500_sectors.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def refresh(check_only=False):
    """Refresh sp500.txt and sp500_sectors.json."""
    df = fetch_sp500_from_wikipedia()

    new_symbols = df['Symbol_yf'].tolist()
    new_sectors = dict(zip(df['Symbol_yf'], df['GICS Sector']))

    current_symbols = load_current_sp500()
    current_set = set(current_symbols)
    new_set = set(new_symbols)

    # Show what changed
    added = new_set - current_set
    removed = current_set - new_set

    print()
    print("=" * 60)
    print("CHANGES")
    print("=" * 60)

    if added:
        print(f"\n  ADDED ({len(added)} new stocks):")
        for sym in sorted(added):
            sector = new_sectors.get(sym, '?')
            print(f"    + {sym:<6} ({sector})")
    else:
        print("\n  No new stocks added.")

    if removed:
        print(f"\n  REMOVED ({len(removed)} stocks no longer in S&P 500):")
        for sym in sorted(removed):
            print(f"    - {sym}")
    else:
        print("\n  No stocks removed.")

    if not added and not removed and current_symbols:
        print("\n  S&P 500 list is already up to date!")
        return False

    if check_only:
        print("\n  (--check mode: no files written)")
        return True

    # Write sp500.txt
    txt_path = os.path.join(os.path.dirname(__file__), 'sp500.txt')
    with open(txt_path, 'w') as f:
        for sym in new_symbols:
            f.write(sym + '\n')
    print(f"\n  Updated: sp500.txt ({len(new_symbols)} stocks)")

    # Update sp500_sectors.json (merge — keep old entries for stocks no longer in S&P)
    old_sectors = load_current_sectors()
    old_sectors.update(new_sectors)
    json_path = os.path.join(os.path.dirname(__file__), 'sp500_sectors.json')
    with open(json_path, 'w') as f:
        json.dump(old_sectors, f, indent=2)
    print(f"  Updated: sp500_sectors.json ({len(old_sectors)} mappings)")

    # Log the change
    log_path = os.path.join(os.path.dirname(__file__), 'sp500_refresh_log.txt')
    with open(log_path, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total stocks: {len(new_symbols)}\n")
        if added:
            f.write(f"Added: {', '.join(sorted(added))}\n")
        if removed:
            f.write(f"Removed: {', '.join(sorted(removed))}\n")
    print(f"  Logged: sp500_refresh_log.txt")

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Refresh S&P 500 stock list from Wikipedia')
    parser.add_argument('--check', action='store_true', help='Show changes without writing files')
    args = parser.parse_args()

    changed = refresh(check_only=args.check)

    if changed and not args.check:
        print("\n" + "=" * 60)
        print("DONE! sp500.txt updated.")
        print("=" * 60)
        print("\nNOTE: If you have cached backtest data, run:")
        print("  python visual_backtest.py --stocks sp500.txt --years 5 --refresh-cache")
        print("This will download ONLY the new stocks and merge into cache.")
    elif args.check:
        print("\n  Run without --check to apply changes.")
    else:
        print("\n  Everything up to date. No action needed.")
