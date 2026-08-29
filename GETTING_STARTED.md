# Getting Started with scanner-us (v2.0)

**Production-ready US stock scanner with multi-timeframe confirmation, cached backtest, and auto-refreshing stock list.**

---

## Quick Start (3 commands)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run quick scan (50 stocks, ~2 min)
python scanner_us.py --mtf-only

# 3. Run 5-year backtest (S&P 500, ~15 min first time, ~5 min after)
python visual_backtest.py --stocks sp500.txt --years 5 --visual
```

Or just double-click **`Scanner.bat`** for a menu-driven interface.

---

## One-Click .bat Files

| File | Purpose | Time |
|---|---|---|
| **`Scanner.bat`** | Main menu (14 options: scans, backtests, charts, verify) | — |
| **`Daily Scan.bat`** | Quick scan — backbone 50, MTF only | ~2 min |
| **`Weekly Scan.bat`** | Full S&P 500 scan, MTF only | ~10 min |
| **`Backtest.bat`** | Backtest menu (3yr/5yr/test) | 3-15 min |

---

## What You Have

```
scanner-us/
├── scanner_us.py              # Main scanner v2.0 (MTF, correct timeframe data)
├── visual_backtest.py         # Cached backtest engine (incremental refresh)
├── chart_generator_v3.py      # Chart generator with pattern overlay
├── verify_picks.py            # Validate entry/SL/targets
├── refresh_sp500.py           # Auto-refresh S&P 500 list from Wikipedia
├── paper_tracker.py           # Paper trade tracker (NEAR waits for breakout)
├── analyze_patterns.py        # Pattern stats by timeframe
├── upgrade_cache.py           # Add monthly data to existing cache
├── Scanner.bat                # Main menu (.bat, 18 options)
├── Daily Scan.bat             # One-click daily scan (S&P 500, best-only)
├── Weekly Scan.bat            # One-click weekly S&P 500 scan (best-only)
├── Backtest.bat               # Backtest menu (.bat)
├── utils/
│   └── sector_rotation_us.py  # S&P sector rotation (11 ETFs)
├── sp500.txt                  # S&P 500 stock list (503 symbols, auto-refreshable)
├── sp500_sectors.json         # Symbol -> GICS sector mapping
├── backbone_us.txt            # Top 50 curated momentum stocks (quick scan)
├── requirements.txt           # Python dependencies
├── README.md                  # Full documentation
├── GETTING_STARTED.md         # This file
├── TECHNICAL_DEEP_DIVE.md     # Architecture + algorithms
└── backtest_results/          # Backtest results + equity curve
    ├── BACKTEST_RESULTS.md
    ├── sp500_5yr_295trades.csv
    ├── equity_curve_sp500_5yr_v2.png
    └── scan_results_2026-08-29.csv
```

---

## Backtest Results (Validated)

### S&P 500 — 5-Year Backtest (293 trades, post C&H Weekly fix)

| Metric | Value |
|---|---|
| **Total trades** | 293 |
| **Win rate** | **69.0%** |
| **Expectancy** | **+1.62% per trade** |
| **Profit factor** | **2.20** |
| **Max drawdown** | -36.3% |
| **Total return** | **+442.1%** |
| **CAGR** | **+40.2%** |

### Pattern breakdown:

| Pattern | Trades | Win Rate | Expectancy | PF | Verdict |
|---|---|---|---|---|---|
| **Double Bottom** | 259 | **71.0%** | **+1.73%** | **2.46** | ✅ Star pattern |
| **C&H Weekly** | 23 | **52.2%** | **+1.65%** | **1.56** | ✅ Good (2nd best) |
| C&H Daily | 11 | 36.4% | -0.37% | 0.84 | ❌ Loser |
| C&H Monthly | 0 | — | — | — | Not detected (rare) |

**Key finding:** C&H Weekly is profitable (+1.65% expectancy). Before the timeframe bug fix, the backtest showed 0 C&H Weekly trades — the bug hid the data.

---

## Daily Workflow

### Step 1: Refresh stock list (weekly)

```powershell
# Check what changed in S&P 500 (no files written)
python refresh_sp500.py --check

# Apply changes (updates sp500.txt + sp500_sectors.json)
python refresh_sp500.py
```

This fetches the latest S&P 500 constituents from Wikipedia. New listings (IPOs added to S&P 500) and delistings (bankruptcies, mergers) are automatically picked up.

### Step 2: Run scan

```powershell
# Quick scan (50 momentum stocks, ~2 min)
python scanner_us.py --mtf-only

# Full S&P 500 scan (~10 min)
python scanner_us.py --stocks sp500.txt --top 50 --mtf-only
```

### Step 3: Verify picks

```powershell
python verify_picks.py
```

### Step 4: Generate charts

```powershell
# Single stock
python chart_generator_v3.py MSFT

# Top 5 from latest scan
python chart_generator_v3.py --batch results_us_2026-08-29.csv --top 5
```

### Step 5: Track picks (paper trading)

```powershell
# Initialize tracker from latest scan
python paper_tracker.py init

# Update daily (fetch prices, check breakouts/SL/T1/T2)
python paper_tracker.py update

# Show all trades
python paper_tracker.py status

# One-line summary
python paper_tracker.py summary
```

**How it works:**
- NEAR picks start as `WAITING_BREAKOUT` — only enter when price crosses breakout level
- BREAKOUT picks enter immediately at breakout price
- Daily update checks: did price hit SL (loss), T1 (hold for T2), T2 (win), or 45-day time exit?
- Tracks P&L%, days held, win rate

---

## Backtest Workflow

### First time (fresh download, ~15 min)

```powershell
# Download 503 stocks + 5 years of data, then backtest
python visual_backtest.py --stocks sp500.txt --years 5 --visual
```

Data is cached to `backtest_cache/all_stocks_5y.pkl`. Future runs load from cache (0.5 min).

### After refreshing stock list (incremental, fast)

When you run `refresh_sp500.py` and new stocks are added to S&P 500, you need to download their history too. But you DON'T need to re-download everything:

```powershell
# Only download NEW stocks, merge into existing cache
python visual_backtest.py --stocks sp500.txt --years 5 --refresh-cache --visual
```

This:
1. Loads existing cache (503 stocks)
2. Compares with current `sp500.txt`
3. Downloads ONLY the new stocks (e.g., 2 new = ~10 seconds)
4. Merges into cache
5. Runs backtest on all stocks

### How the cache works

| Situation | What happens | Time |
|---|---|---|
| First run | Download all 503 stocks | ~3 min |
| Run again next day | Load from cache (< 24h old) | 0.5 min |
| Run after `refresh_sp500.py` | `--refresh-cache` downloads only new stocks | ~10 sec per stock |
| Cache > 24h old | Full re-download | ~3 min |

---

## Command Reference

```powershell
# === Scans ===
python scanner_us.py --mtf-only --best-only                    # S&P 500 (default), 1 per stock
python scanner_us.py --stocks sp500.txt --top 50 --mtf-only    # S&P 500, all setups
python scanner_us.py --stocks backbone_us.txt --mtf-only --best-only --no-refresh  # quick 50
python scanner_us.py --test --mtf-only --no-refresh            # test mode (10 stocks)
python scanner_us.py --mtf-only --db-only                      # Double Bottom only (71% WR)
python scanner_us.py --mtf-only --db-only --best-only          # DB only, 1 per stock

# === Backtest ===
python visual_backtest.py --stocks sp500.txt --years 5 --visual          # Full backtest
python visual_backtest.py --stocks backbone_us.txt --years 3 --visual    # Backbone 3yr
python visual_backtest.py --stocks sp500.txt --years 5 --refresh-cache   # Incremental cache
python visual_backtest.py --test --years 1 --visual                      # Test mode

# === Stock List Refresh ===
python refresh_sp500.py --check    # Show what changed (dry run)
python refresh_sp500.py            # Apply changes to sp500.txt + sectors

# === Paper Tracker ===
python paper_tracker.py init       # Init from latest scan CSV
python paper_tracker.py update     # Fetch prices, check breakouts/SL/T1/T2
python paper_tracker.py status     # Show all trades
python paper_tracker.py summary    # One-line summary

# === Charts ===
python chart_generator_v3.py MSFT                                    # Single stock
python chart_generator_v3.py --batch results_us_2026-08-29.csv --top 5  # Top 5 from scan

# === Validation ===
python verify_picks.py              # Validate entry/SL/targets

# === Analysis ===
python analyze_patterns.py backtest_results/sp500_5yr_295trades.csv  # Pattern stats

# === Sector Rotation ===
python -c "from utils.sector_rotation_us import print_sector_heatmap; print_sector_heatmap()"
```

---

## Pro Tips

### Tip 1: Refresh stock list monthly
S&P 500 changes a few times/year. Run `python refresh_sp500.py --check` monthly to see what changed. New IPOs added to S&P 500 could be high-momentum winners.

### Tip 2: Use --refresh-cache after refresh
After `refresh_sp500.py` adds new stocks, run backtest with `--refresh-cache` to download only the new stocks. Don't re-download all 503.

### Tip 3: Double Bottom is the star (71% WR)
259 of 293 backtest trades were Double Bottom (88%). 71.0% win rate, +1.73% expectancy. Use `--db-only` to see only these. Most days = 0 setups. Wait for them.

### Tip 4: C&H Weekly is the 2nd-best pattern (52% WR)
23 trades, 52.2% WR, +1.65% expectancy. This was hidden by a bug (daily data used for all timeframes). Now fixed — C&H Weekly is profitable.

### Tip 5: Avoid Cup & Handle Daily
36.4% win rate, -0.37% expectancy in backtest. Consider filtering out with `--db-only` or ignoring C&H Daily setups.

### Tip 6: MTF filter saves you in bear markets
The weekly 50-SMA filter kept the scanner OUT of the 2022 bear market (10 months of zero trades). This alone prevented major losses.

### Tip 7: Use --best-only to avoid duplicates
Without `--best-only`, the same stock appears 3x (Monthly + Weekly + Daily). With `--best-only`, you see 1 setup per stock (highest score). 26 setups → 10 unique stocks.

### Tip 8: Paper trade before risking real money
Run `python paper_tracker.py init` after each scan, then `python paper_tracker.py update` daily. Track which picks hit T1 vs SL. Compare to backtest expectancy (+1.62%).

---

## FAQs

**Q: Do I get new stocks every day?**
A: You get new **setups** every day (different breakouts, different statuses) from the same stock list. The stock list itself (`sp500.txt`) auto-refreshes from Wikipedia before each scan.

**Q: Why did the scanner default change from backbone to S&P 500?**
A: backbone_us.txt only has 50 curated stocks. You were missing 450+ S&P 500 stocks with high-quality setups (MSI, CTSH, ICE, TRV, etc.). Now defaults to sp500.txt with auto-refresh.

**Q: How often should I refresh the stock list?**
A: It auto-refreshes before each scan (from Wikipedia). Use `--no-refresh` to skip for faster startup. S&P 500 changes a few times/year.

**Q: What happens to cache when new stocks are added?**
A: Run `python visual_backtest.py --refresh-cache` — it only downloads the NEW stocks and merges into existing cache. No need to re-download all 503.

**Q: Should I backtest or trade live first?**
A: **Always backtest first.** The 5-year S&P 500 backtest (293 trades, 69% win rate) gives you confidence the system works. Then paper trade with `paper_tracker.py`.

**Q: Which patterns should I trade?**
A: Double Bottom (71% WR, +1.73% exp) and C&H Weekly (52.2% WR, +1.65% exp). Avoid C&H Daily (36.4% WR, -0.37% exp). Use `--db-only` for Double Bottoms only.

**Q: Why does --best-only show fewer setups?**
A: Without `--best-only`, the same stock appears 3x (Monthly + Weekly + Daily = same trade). With `--best-only`, you see 1 setup per stock (highest score). 26 setups → 10 unique stocks.

**Q: Can I trade these in India?**
A: No. You need a US broker (Webull, Interactive Brokers, TD Ameritrade). OR use for YouTube content only.

---

**Created:** 2026-08-28
**Updated:** 2026-08-29 (C&H Weekly fix, paper tracker, auto-refresh, quality filters)
**Status:** VALIDATED (293 trades, 69% win rate, +1.62% expectancy, C&H Weekly now profitable)
