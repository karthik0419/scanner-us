"""
Weekly Swing Setup Scanner  v3  — Production

Built on scanner-v2 (proven +2.7% expectancy, 35% win rate, 3:1 R:R).
Improvements driven by performance verification of 414 picks (May-Jul 2026):

  1. ATR-based tighter stop loss (v2 avg SL loss was -6.5%; earnings-scanner
     proved -3% stops work). Optional: --sl-mode atr|original
  2. Double Bottom promoted (100% win rate in verification — 11W/0L)
  3. Channel Breakout tightened (was 24% win rate — added volume + RSI gates)
  4. Trailing stop after T1 (T2 was rarely hit — 3/97 closed trades)
  5. Price range filter (--min-price 100 --max-price 400) for retail-friendly
     high-momentum stocks
  6. Self-contained sector rotation (no external dependency on scanner/)
  7. Bearish / short setups from weak sectors (NSE Heat Map strategy)
  8. Volume-weighted scoring refinement

Usage:
  python scanner.py                          # full scan, top 30
  python scanner.py --top 50
  python scanner.py --min-score 50
  python scanner.py --min-price 100 --max-price 400   # retail filter
  python scanner.py --sl-mode atr            # ATR-based stops
  python scanner.py --bearish                # scan for short setups
  python scanner.py --test                   # quick test on 50 stocks
"""

import os, sys, time, argparse, warnings, logging
import pandas as pd
import numpy as np
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")
# Suppress yfinance "possibly delisted" error spam — these are handled
# gracefully by the fallback chain (yfinance → jugaad-data → bhavcopy)
for _n in ["yfinance", "urllib3", "peewee", "asyncio"]:
    logging.getLogger(_n).setLevel(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.nse_eq import fetch_nse_eq_universe
from data.loader import _fetch_nse, _resample_weekly

# Tuned detectors (v2 — proven)
from patterns.cup_handle         import detect_cup_handle, detect_cup_handle_weekly
from patterns.cup_handle_monthly import detect_cup_handle_monthly, resample_monthly
from patterns.double_bottom      import detect_double_bottom
from patterns.wedge              import detect_descending_wedge
from patterns.breakout           import detect_breakout
from patterns.break_retest       import detect_break_retest
from patterns.channel            import detect_descending_channel, detect_ascending_channel
from patterns.triangle           import detect_triangle
from patterns.darvas_box         import detect_darvas_box
from patterns.flags              import detect_flag_pennant
from patterns.sr_levels          import detect_sr_levels
from patterns.retest             import detect_retest
from patterns.compression        import detect_compression

# Self-contained sector rotation (v3 — no external dependency)
from utils.sector_rotation_v3 import get_sector_bonus, print_sector_heatmap, get_sector_heat

# Market regime filter (Nifty vs 200DMA) — 5yr backtest showed longs lose in RISK_OFF
from utils.regime import get_market_regime, print_regime_banner

# Telegram notification (auto-sends after scan completes)
from telegram_notify import notify_scan_results

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MIN_CANDLES = 140
MAX_WORKERS = 4


# ── ATR calculation ──────────────────────────────────────────────────────
def _calc_atr(df, period=14):
    """Calculate Average True Range."""
    if df is None or len(df) < period + 1:
        return 0
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    tr = np.zeros(len(df))
    for i in range(1, len(df)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )
    return float(np.mean(tr[-period:]))


# ── ATR-based stop loss ──────────────────────────────────────────────────
def _atr_stop_loss(df, breakout, atr, multiplier=2.0):
    """ATR-based stop: breakout - (multiplier * ATR).
    Tighter than v2's handle_low * 0.98 which often gave -8% to -15% losses.
    multiplier=2.0 gives ~4-6% stop on typical NSE stocks.
    (2.0x chosen over 1.5x after ATR sweep: PF 2.03 vs 1.80, DD -46.8% vs -66.7%)"""
    if atr <= 0:
        return breakout * 0.96  # fallback: 4% below breakout
    stop = breakout - (multiplier * atr)
    return round(stop, 2)


# ── Pattern detection (same priority as v2, Double Bottom promoted) ─────
def _detect_pattern(df_daily, df_weekly, timeframe_filter=None):
    """Detect pattern on daily/weekly/monthly. Returns result dict or None.

    Args:
        df_daily: daily OHLCV dataframe
        df_weekly: weekly OHLCV dataframe
        timeframe_filter: if set ('daily', 'weekly', 'monthly', 'all'),
                          only detect patterns on that timeframe.
                          Default None = all timeframes (current behavior).
    The result dict gets a 'timeframe' key added ('Daily', 'Weekly', or 'Monthly').
    """
    tf = (timeframe_filter or 'all').lower()

    # Monthly patterns
    if tf in ('all', 'monthly'):
        dfm = resample_monthly(df_daily)
        result = detect_cup_handle_monthly(dfm)
        if result:
            result['timeframe'] = 'Monthly'
            return result

    # Weekly patterns
    if tf in ('all', 'weekly'):
        result = detect_cup_handle_weekly(df_weekly)
        if result:
            result['timeframe'] = 'Weekly'
            return result

    # Daily patterns
    if tf in ('all', 'daily'):
        result = (
            detect_cup_handle(df_daily) or
            detect_double_bottom(df_daily) or          # promoted: 100% win rate
            detect_descending_channel(df_daily) or
            detect_ascending_channel(df_daily) or
            detect_triangle(df_daily) or
            detect_darvas_box(df_daily) or
            detect_flag_pennant(df_daily) or
            detect_descending_wedge(df_daily) or
            detect_sr_levels(df_daily) or
            detect_break_retest(df_daily) or
            detect_retest(df_daily) or
            detect_compression(df_daily) or
            detect_breakout(df_daily)
        )
        if result:
            result['timeframe'] = 'Daily'
            return result

    return None


# ── Targets with trailing stop logic ─────────────────────────────────────
def _add_targets(result):
    breakout = result.get("breakout", 0)
    target2  = result.get("target", 0)
    if breakout > 0 and target2 > breakout:
        move = target2 - breakout
        result["target_1"] = round(breakout + move * 0.50, 2)  # was 0.60 — 50% of measured move is more realistic for swings
        result["target_2"] = round(target2, 2)
    else:
        result["target_1"] = result.get("target", 0)
        result["target_2"] = result.get("target", 0)
    return result


# ── Scoring (v3 — Double Bottom promoted, Channel Breakout demoted) ─────
def _score(result):
    cmp      = result.get("cmp", 0)
    target   = result.get("target_1", result.get("target", 0))
    stop     = result.get("stop_loss", 0)
    breakout = result.get("breakout", 0)

    if cmp <= 0 or stop <= 0 or stop >= cmp:
        return 0, 0

    # R:R calculated from BREAKOUT entry price (where you'd actually enter),
    # not from CMP (which may be below breakout for NEAR/WATCH picks).
    # For BREAKOUT picks, entry ≈ CMP, so this is the same.
    entry = breakout if breakout > 0 and breakout <= cmp * 1.02 else cmp
    upside = (target - entry) / entry * 100
    risk   = (entry - stop) / entry * 100
    rr     = upside / risk if risk > 0 else 0

    # Penalty for wide stops (>6% risk from entry)
    if risk > 8:
        rr *= 0.5  # halve R:R for excessive risk
    elif risk > 6:
        rr *= 0.8  # 20% penalty for wide risk

    score = 0
    if rr >= 3:   score += 40
    elif rr >= 2: score += 30
    elif rr >= 1: score += 15

    if result.get("volume"):                  score += 20
    status = result.get("status", "")
    if status == "BREAKOUT": score += 25
    elif status == "NEAR":   score += 12
    elif status == "WATCH":  score += 5

    dist = abs(cmp - breakout) / breakout if breakout else 1
    if dist < 0.02:   score += 20
    elif dist < 0.05: score += 12
    elif dist < 0.10: score += 6

    # v3: Pattern bonuses adjusted based on verification data
    # Double Bottom: 100% win rate (11W/0L) — promoted from 18 to 28
    # Channel Breakout (Descending): 24% win rate — demoted from 22 to 12
    # Channel Breakout (Ascending): demoted from 18 to 10
    # Cup & Handle: 42% win rate — kept at 20 (workhorse)
    # Cup & Handle (Weekly): 50% win rate in scanner/ — promoted from 25 to 28
    pat = result.get("pattern", "")
    tf  = result.get("timeframe", "Daily")
    # Lookup key combines pattern + timeframe for C&H (different bonuses per TF)
    pat_tf = f"{pat} [{tf}]" if "Cup & Handle" in pat else pat
    pat_bonus = {
        "Cup & Handle [Monthly]":        30,
        "Cup & Handle [Weekly]":         28,   # promoted (was 25)
        "Cup & Handle":                  20,
        "Double Bottom":                 28,   # promoted (was 18) — 100% win rate
        "Ascending Triangle":            15,
        "Symmetrical Triangle":          12,
        "Darvas Box":                    15,
        "Bullish Flag":                  12,
        "Descending Wedge":              8,    # demoted (was 14) — 27.8% WR over 5yr/223 trades
        "Break & Retest":                10,
        "S&R Breakout":                  14,   # promoted (was 10) — 52.3% WR over 5yr/130 trades
        "Channel Breakout (Descending)": 12,   # demoted (was 22) — 24% win rate
        "Channel Breakout (Ascending)":  10,   # demoted (was 18)
        "Channel Breakout":              8,    # demoted (was 10)
        "S&R Support":                   22,   # promoted (was 10) — 63% WR / +4.79% avg over 5yr
        "Resistance Breakout":           10,
    }
    score += pat_bonus.get(pat_tf, pat_bonus.get(pat, 5))
    # Normalise to 0-100 (max theoretical ~155)
    normalised = round(min(score / 155 * 100, 100), 1)
    return normalised, round(rr, 2)


# ── Apply ATR stop loss if requested ─────────────────────────────────────
def _apply_sl_mode(result, df, sl_mode):
    """Override stop loss with ATR-based calculation if --sl-mode atr.
    Uses hybrid approach: keeps original structural stops for C&H/Wedge
    (handle low / wedge low are structurally meaningful), uses ATR stops
    for patterns without structural stops (S&R, Breakout, etc.).
    ALWAYS caps max risk at 8% — if structural stop is wider, tighten to ATR."""
    pat = result.get("pattern", "")
    cmp = result.get("cmp", 0)
    current_stop = result.get("stop_loss", 0)
    current_risk = (cmp - current_stop) / cmp if cmp else 0
    MAX_RISK = 0.08  # 8% max stop loss from CMP

    # If structural stop is already within 8%, keep it (no change needed)
    if current_risk <= MAX_RISK and sl_mode != "atr":
        return result

    # If structural stop is too wide (>8%), always try ATR regardless of pattern
    atr = _calc_atr(df, period=14)

    if sl_mode == "atr" and current_risk <= MAX_RISK:
        # ATR mode requested but structural stop is fine — only override for non-structural patterns
        KEEP_ORIGINAL_STOP = {
            "Cup & Handle":             True,   # handle low is structural
            "Descending Wedge":         True,   # wedge low is structural
        }
        if "Cup & Handle" in pat or KEEP_ORIGINAL_STOP.get(pat, False):
            return result  # keep original stop

    # Either: ATR mode + non-structural pattern, OR structural stop too wide (>8%)
    if atr <= 0:
        # No ATR — just cap at 8% max
        if current_risk > MAX_RISK:
            result["stop_loss"] = round(cmp * (1 - MAX_RISK), 2)
            result["stop_capped"] = True
        return result

    breakout = result.get("breakout", 0)
    new_stop = _atr_stop_loss(df, breakout, atr, multiplier=2.0)
    if new_stop > 0 and new_stop < cmp:
        max_stop_drop = cmp * (1 - MAX_RISK)  # max 8% stop
        new_stop = max(new_stop, max_stop_drop)
        new_risk = (cmp - new_stop) / cmp
        if new_risk <= MAX_RISK:
            result["stop_loss"] = new_stop
            result["atr"] = round(atr, 2)
            result["atr_mult"] = 2.0
            if current_risk > MAX_RISK:
                result["stop_tightened"] = True  # flag: structural stop was too wide
        else:
            # ATR stop also too wide — hard cap at 8%
            result["stop_loss"] = round(max_stop_drop, 2)
            result["stop_capped"] = True
    elif current_risk > MAX_RISK:
        # ATR calc failed but structural stop too wide — hard cap
        result["stop_loss"] = round(cmp * (1 - MAX_RISK), 2)
        result["stop_capped"] = True
    return result


# ── Price range filter ───────────────────────────────────────────────────
def _price_filter(cmp, min_price, max_price):
    """Filter stocks by price range. Returns True if stock passes."""
    if min_price is not None and cmp < min_price:
        return False
    if max_price is not None and cmp > max_price:
        return False
    return True


# ── Parallel data fetch ──────────────────────────────────────────────────
def _fetch_parallel(symbols, workers=MAX_WORKERS):
    print(f"  Pre-fetching price data ({workers} workers)...")
    results = {}
    total = len(symbols)
    done = 0
    BATCH = 300
    for i in range(0, total, BATCH):
        batch = symbols[i:i+BATCH]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_nse, s.replace(".NS",""), 730): s for s in batch}
            try:
                for f in as_completed(futures, timeout=120):
                    done += 1
                    sym = futures[f]
                    try:
                        df = f.result(timeout=15)
                        if df is not None and len(df) >= MIN_CANDLES:
                            results[sym] = df
                    except Exception:
                        pass
                    if done % 100 == 0:
                        print(f"    {done}/{total} fetched...")
            except Exception:
                done += len(batch) - len([f for f in futures if f.done()])
                print(f"    Batch timeout at {done}/{total} — continuing...")
    print(f"  Ready: {len(results)} stocks")
    return results


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Weekly Swing Scanner v3")
    parser.add_argument("--top",        type=int,   default=30)
    parser.add_argument("--min-score",  type=float, default=50)
    parser.add_argument("--workers",    type=int,   default=MAX_WORKERS)
    parser.add_argument("--test",       action="store_true")
    parser.add_argument("--stocks",     type=str,   default=None,
                        help="Custom stock list file (one symbol per line, e.g. nifty200.txt)")
    parser.add_argument("--sl-mode",    choices=["original", "atr"], default="atr",
                        help="Stop loss mode: atr (default, tighter) or original (v2)")
    parser.add_argument("--min-price",  type=float, default=None,
                        help="Minimum stock price filter (e.g. 100)")
    parser.add_argument("--max-price",  type=float, default=None,
                        help="Maximum stock price filter (e.g. 400)")
    parser.add_argument("--bearish",    action="store_true",
                        help="Scan for bearish/short setups in weak sectors")
    parser.add_argument("--no-notify",  action="store_true",
                        help="Skip Telegram notification (default: auto-send on completion)")
    parser.add_argument("--env-file",   type=str,   default=None,
                        help="Which .env file to load Telegram creds from (e.g. .env.swingiq for prod bot)")
    parser.add_argument("--no-sync",    action="store_true",
                        help="Skip paper tracker sync (default: auto-sync on completion)")
    parser.add_argument("--smart",      action="store_true",
                        help="Use smart universe: Backbone50 + Nifty500 + hot sector stocks (adapts daily)")
    parser.add_argument("--timeframe",  type=str,  default="all",
                        choices=["all", "daily", "weekly", "monthly"],
                        help="Filter by timeframe: all (default), daily, weekly, monthly")
    parser.add_argument("--defensive",  action="store_true",
                        help="Auto-filter to defensive sectors (Pharma, IT, FMCG) in choppy/bear markets")
    args = parser.parse_args()

    # --test is a smoke test: suppress real-world side effects so test runs
    # don't pollute the live paper tracker or send Telegram alerts.
    if args.test:
        args.no_notify = True
        args.no_sync = True

    print("=" * 70)
    print("  SWING SCANNER  v3  — PRODUCTION")
    print(f"  Full NSE EQ Universe | {date.today()}")
    print(f"  SL mode: {args.sl_mode} | Price filter: "
          f"{args.min_price or 0}-{args.max_price or 'inf'} | "
          f"Direction: {'BEARISH' if args.bearish else 'BULLISH'}"
          + ("  [TEST — notify/sync OFF]" if args.test else ""))
    print("=" * 70)

    # Market regime check (Nifty vs 200DMA)
    regime = get_market_regime()
    print_regime_banner(regime, bearish=args.bearish, defensive_filter=args.defensive)

    print("\n[1/4] Loading NSE EQ universe...")
    if args.smart:
        # Smart universe: Backbone50 + Nifty500 + ALL stocks in today's hot sectors
        # Adapts daily to market heat — not a static list
        import json
        from utils.sector_rotation_v3 import get_sector_heat
        # Load backbone
        backbone_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backbone50.txt")
        if os.path.exists(backbone_path):
            with open(backbone_path) as f:
                backbone = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            backbone = [s if s.endswith('.NS') else s + '.NS' for s in backbone]
        else:
            backbone = []
        # Load nifty500
        n500_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty500.txt")
        n500 = []
        if os.path.exists(n500_path):
            with open(n500_path) as f:
                n500 = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            n500 = [s if s.endswith('.NS') else s + '.NS' for s in n500]
        # Get today's hot sectors from sector heat
        try:
            heat = get_sector_heat()
            # heat is dict of {sector: {'5d': pct, '20d': pct, 'signal': str}}
            sector_perf = [(s, d.get('5d', 0), d.get('signal', '')) for s, d in heat.items()]
            sector_perf.sort(key=lambda x: x[1], reverse=True)
            hot_sectors = [s for s, p, _ in sector_perf[:2] if p > 0]
            print(f"  Hot sectors today: {', '.join(hot_sectors)}")
            # Load sector stock map
            sectors_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nse_sectors.json")
            hot_stocks = []
            if os.path.exists(sectors_file):
                with open(sectors_file) as f:
                    stock_sectors = json.load(f)
                # Map sector names (heat uses short names like 'IT', 'BANK')
                SECTOR_NAME_MAP = {
                    'METAL': 'Metals', 'AUTO': 'Auto', 'BANK': 'Banking',
                    'IT': 'IT', 'PHARMA': 'Pharma', 'FMCG': 'FMCG',
                    'REALTY': 'Realty', 'ENERGY': 'Energy', 'INFRA': 'Infra',
                    'MEDIA': 'Media', 'PSU': 'PSU Bank', 'MIDCAP': 'MidCap',
                    'FINANCIAL SERVICES': 'Banking', 'BANK NIFTY': 'Banking',
                }
                target = set()
                for s in hot_sectors:
                    target.add(SECTOR_NAME_MAP.get(s.upper(), s.capitalize()))
                for sym_ns, sector in stock_sectors.items():
                    if sector in target:
                        sym = sym_ns if sym_ns.endswith('.NS') else sym_ns + '.NS'
                        hot_stocks.append(sym)
            print(f"  Hot sector stocks: {len(hot_stocks)}")
        except Exception as e:
            print(f"  Sector heat unavailable ({e}) — using backbone + nifty500 only")
            hot_stocks = []
        # Combine + dedupe
        symbols = list(dict.fromkeys(backbone + n500 + hot_stocks))
        print(f"  Smart universe: {len(backbone)} backbone + {len(n500)} nifty500 + {len(hot_stocks)} hot sector = {len(symbols)} stocks")
    elif args.stocks:
        # Use custom stock list file (one symbol per line, with or without .NS)
        if os.path.exists(args.stocks):
            with open(args.stocks) as f:
                symbols = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            symbols = [s if s.endswith('.NS') else s + '.NS' for s in symbols]
            print(f"  Custom list: {args.stocks} ({len(symbols)} stocks)")
        else:
            print(f"  File not found: {args.stocks}")
            return
    else:
        symbols = fetch_nse_eq_universe()
    if not symbols:
        print("  Failed. Exiting.")
        return
    if args.test:
        symbols = symbols[:50]
        print(f"  TEST MODE: {len(symbols)} stocks")
    else:
        print(f"  Universe: {len(symbols)} stocks")

    # Sector heatmap
    print("\n  Sector Rotation Heatmap:")
    try:
        heat = get_sector_heat()
        print_sector_heatmap()
    except Exception:
        heat = {}

    print(f"\n[2/4] Pre-fetching price data...")
    price_cache = _fetch_parallel(symbols, args.workers)

    # Price filter on pre-fetched data
    if args.min_price or args.max_price:
        filtered = {}
        for sym, df in price_cache.items():
            cmp = float(df['Close'].iloc[-1])
            if _price_filter(cmp, args.min_price, args.max_price):
                filtered[sym] = df
        print(f"  Price filter ({args.min_price or 0}-{args.max_price or 'inf'}): "
              f"{len(filtered)}/{len(price_cache)} stocks passed")
        price_cache = filtered

    print(f"\n[3/4] Scanning {len(price_cache)} stocks...\n")
    results = []
    all_results = []
    for sym, df in price_cache.items():
        try:
            df_weekly = _resample_weekly(df)
            result = _detect_pattern(df, df_weekly, timeframe_filter=args.timeframe)
            if not result:
                continue
            result = _add_targets(result)
            result = _apply_sl_mode(result, df, args.sl_mode)
            score, rr = _score(result)
            if rr <= 0:
                continue

            cmp  = result.get("cmp", 0)
            t1   = result.get("target_1", 0)
            t2   = result.get("target_2", 0)
            stop = result.get("stop_loss", 0)
            bo   = result.get("breakout", 0)

            # Max risk filter: reject picks with >10% stop loss from CMP
            risk_pct = (cmp - stop) / cmp * 100 if cmp else 0
            if risk_pct > 10:
                continue  # too risky — skip entirely

            # Max distance filter: reject picks >8% from breakout (won't trigger soon)
            dist_pct = abs(bo - cmp) / cmp * 100 if bo and cmp else 0
            if bo > 0 and dist_pct > 8 and result.get("status") != "BREAKOUT":
                continue  # too far from breakout to be actionable

            # Learning #8: Skip if <10% upside remaining from CMP to T2
            upside_remaining = (t2 - cmp) / cmp * 100 if cmp and t2 > cmp else 0
            if upside_remaining < 10:
                continue  # most of move already done — not worth entering

            # Sector rotation
            try:
                sector_name, sector_signal, sector_bonus = get_sector_bonus(sym)
                score = round(min(score + (sector_bonus / 155 * 100), 100), 1)
            except Exception:
                sector_name, sector_signal = "Unknown", "Unknown"

            # Bearish mode: only keep stocks in WEAK/COOLING sectors
            if args.bearish and sector_signal not in ("WEAK", "COOLING"):
                continue

            # Learning #1: % of measured move done / left
            measured_move = t2 - bo if (t2 > bo and bo > 0) else 0
            pct_done = round((cmp - bo) / measured_move * 100, 1) if measured_move > 0 else 0.0
            pct_left = round(100 - pct_done, 1)

            # Learning #4: Breakout sustained — held above BO ≥10 trading days
            sustained = False
            if bo > 0 and len(df) >= 20:
                days_above = int((df['Close'].tail(20) >= bo).sum())
                sustained = days_above >= 10

            # Learning #5: Nested cup — run a second cup length to detect nesting
            nested = False
            try:
                from patterns.cup_handle import detect_cup_handle
                from patterns.cup_handle_monthly import detect_cup_handle_monthly, resample_monthly
                # Count how many cup detectors fire on this stock
                cup_hits = 0
                if detect_cup_handle(df): cup_hits += 1
                if detect_cup_handle_weekly(df_weekly): cup_hits += 1
                dfm = resample_monthly(df)
                if detect_cup_handle_monthly(dfm): cup_hits += 1
                nested = cup_hits >= 2
                if nested:
                    score = round(min(score + (10 / 155 * 100), 100), 1)
            except Exception:
                pass

            # Learning #3: Double confirmation — descending channel + S&R near same level
            double_confirm = False
            try:
                from patterns.channel import detect_descending_channel
                from patterns.sr_levels import detect_sr_levels
                ch = detect_descending_channel(df)
                sr = detect_sr_levels(df)
                if ch and sr:
                    ch_bo = ch.get('breakout', 0)
                    sr_bo = sr.get('breakout', 0)
                    if ch_bo > 0 and sr_bo > 0:
                        diff_pct = abs(ch_bo - sr_bo) / ch_bo * 100
                        if diff_pct < 2:
                            double_confirm = True
                            score = round(min(score + (15 / 155 * 100), 100), 1)
            except Exception:
                pass

            # Learning #2: Historical resistance near T2
            hist_resist = None
            try:
                if len(df) >= 100 and t2 > 0:
                    hist = df.iloc[-200:-50] if len(df) >= 200 else df.iloc[:-50]
                    if len(hist) > 0:
                        prior_high = float(hist['High'].max())
                        if abs(prior_high - t2) / t2 < 0.10:
                            hist_resist = round(prior_high, 2)
            except Exception:
                pass

            # Use breakout as entry for upside/risk columns (where you'd actually enter)
            entry = bo if bo > 0 and bo <= cmp * 1.02 else cmp
            row = {
                "symbol":           sym,
                "pattern":          result.get("pattern"),
                "timeframe":        result.get("timeframe", "Daily"),
                "status":           result.get("status"),
                "cmp":              round(cmp, 2),
                "breakout":         round(bo, 2),
                "stop_loss":        round(stop, 2),
                "target_1":         round(t1, 2),
                "target_2":         round(t2, 2),
                "upside_%":         round((t1 - entry) / entry * 100, 2) if entry else 0,
                "risk_%":           round((entry - stop) / entry * 100, 2) if entry else 0,
                "upside_remaining": round(upside_remaining, 1),
                "pct_done":         pct_done,
                "pct_left":         pct_left,
                "sustained":        sustained,
                "nested_cup":       nested,
                "double_confirm":   double_confirm,
                "hist_resist":      hist_resist if hist_resist else "",
                "rr":               rr,
                "volume":           result.get("volume", False),
                "neckline":         result.get("neckline_kind", ""),
                "sector":           sector_name,
                "sector_signal":    sector_signal,
                "score":            score,
            }
            if "atr" in result:
                row["atr"] = result["atr"]
            
            # Strong sector filter (if enabled and market is choppy/bear)
            skip_weak_sector = False
            if args.defensive and regime and regime["status"] in ["CHOPPY", "BEAR"]:
                strong_sectors = regime.get("strong_sectors", [])
                if strong_sectors and sector_name not in strong_sectors:
                    skip_weak_sector = True
            
            below_cutoff = score < args.min_score
            if skip_weak_sector:
                # Skip this stock - not in strong sectors
                pass
            elif below_cutoff:
                all_results.append(row)
            else:
                results.append(row)

            flags = ("".join([
                " [S]" if sustained else "",
                " [N]" if nested else "",
                " [D]" if double_confirm else "",
                f" ~R{hist_resist:.0f}" if hist_resist else "",
            ])).strip()
            print(f"  {sym:<20} FOUND | {result.get('pattern')} [{result.get('timeframe','Daily')}] | "
                  f"{result.get('status')} | score={score} | rr={rr} | "
                  f"{pct_done:.0f}%done {pct_left:.0f}%left | {flags}")
        except Exception:
            continue

    print(f"\n[4/4] Saving results...")
    if not results:
        print("  No setups found.")
        return

    df_out   = pd.DataFrame(results).sort_values("score", ascending=False).head(args.top)
    prefix = "v3" if not args.bearish else "v3_bearish"
    out_path = os.path.join(RESULTS_DIR, f"{prefix}_{date.today()}.csv")
    df_out.to_csv(out_path, index=False)

    if all_results:
        df_all = pd.DataFrame(results + all_results).sort_values("score", ascending=False)
        all_path = os.path.join(RESULTS_DIR, f"{prefix}_{date.today()}_all.csv")
        df_all.to_csv(all_path, index=False)
        print(f"  Extended list  : {all_path}  ({len(df_all)} stocks)")

    print(f"\n{'='*70}")
    print(f"  SCAN COMPLETE — {date.today()}")
    print(f"  Setups found : {len(results)}")
    print(f"  Top score    : {df_out['score'].iloc[0]} ({df_out['symbol'].iloc[0]})")
    print(f"{'='*70}")
    print(f"\n  TOP {len(df_out)} SETUPS")
    print(f"  {'Symbol':<20} {'Pattern':<28} {'TF':<8} {'Score':>5} {'RR':>5} {'T1%':>7} {'SL%':>6} {'Status'}")
    print("  " + "-"*95)
    for _, row in df_out.iterrows():
        tf = row.get('timeframe', 'Daily')
        print(f"  {row['symbol']:<20} {row['pattern']:<28} {tf:<8} {row['score']:>5} "
              f"{row['rr']:>5} {row['upside_%']:>6}% {row['risk_%']:>5}%  {row['status']}")

    print(f"\n  Saved: {out_path}")
    print(f"{'='*70}\n")

    # Auto-send to Telegram (unless --no-notify)
    if not args.no_notify:
        print("[Telegram] Notifying...")
        notify_scan_results(csv_path=out_path, top=10, bearish=args.bearish, env_file=args.env_file)
        print()

    # Auto-sync paper tracker with new scan picks
    if not args.no_sync:
        print("[Paper Tracker] Syncing...")
        try:
            from paper_tracker import sync_tracker
            sync_tracker(csv_path=out_path)
        except Exception as e:
            print(f"  Sync skipped: {e}")
        print()

    # Post-scan: offer to check breakouts + re-entries (interactive prompt)
    if not args.no_sync and sys.stdin.isatty():
        print("=" * 70)
        print("  POST-SCAN OPTIONS")
        print("=" * 70)
        print("  1. Check breakouts + re-entries now (fetch live prices)")
        print("  2. Show tracker status")
        print("  3. Skip — exit")
        print()
        try:
            post_choice = input("  Choice [1-3, default=3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            post_choice = "3"

        if post_choice == "1":
            print("\n[Paper Tracker] Fetching prices + checking breakouts + re-entries...")
            try:
                from paper_tracker import update_tracker, show_status
                update_tracker()
                print()
                show_status()
            except Exception as e:
                print(f"  Update failed: {e}")
            print()
        elif post_choice == "2":
            print()
            try:
                from paper_tracker import show_status
                show_status()
            except Exception as e:
                print(f"  Status failed: {e}")
            print()


if __name__ == "__main__":
    main()
