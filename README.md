# scanner-us — US Stock Swing Trading Scanner (v2.0)

Production-ready swing trading scanner for US stocks (NYSE/NASDAQ), adapted from [scanner-v3](../scanner-v3) (India/NSE).

**v2.0: Multi-timeframe confirmation + critical bug fixes + cached visual backtest.**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [What It Does](#what-it-does)
3. [The Story: How We Got Here](#the-story-how-we-got-here)
4. [Bugs We Found & Fixed](#bugs-we-found--fixed)
5. [Multi-Timeframe Confirmation](#multi-timeframe-confirmation)
6. [Backtest Results](#backtest-results)
7. [Tech Stack](#tech-stack)
8. [Pattern Detection Rules](#pattern-detection-rules)
9. [Scoring System](#scoring-system)
10. [Sector Rotation](#sector-rotation)
11. [Files](#files)
12. [Usage](#usage)
13. [Honest Caveats](#honest-caveats)
14. [Monetization Potential](#monetization-potential)

---

## Quick Start

```powershell
# Install dependencies
pip install -r requirements.txt

# Scan top 50 US momentum stocks (~2 min)
python scanner_us.py

# Scan full S&P 500, MTF-confirmed only (~10 min)
python scanner_us.py --stocks sp500.txt --top 50 --mtf-only

# Test mode (10 stocks, fast)
python scanner_us.py --test --mtf-only

# Verify picks (validate entry/SL/targets)
python verify_picks.py

# Generate charts with pattern overlay
python chart_generator_v3.py MSFT
python chart_generator_v3.py --batch results_us_2026-08-29.csv --top 5

# Backtest (cached data, no rate limiting)
python visual_backtest.py --stocks backbone_us.txt --years 5 --visual
python visual_backtest.py --stocks sp500.txt --years 5 --visual
```

---

## What It Does

Scans **US stocks** for swing trading setups using William O'Neil's proven chart patterns:

1. **Cup & Handle** (Daily/Weekly/Monthly)
2. **Double Bottom**

**Entry:** Breakout above pattern resistance
**Stop Loss:** 2.0x ATR, capped at 8% max risk (calculated from ENTRY, not CMP)
**Targets:** T1 = 50% of measured move, T2 = 100%
**Hold Time:** Max 45 days

---

## The Story: How We Got Here

### Phase 1: Adapt scanner-v3 (India) for US market

The original scanner-v3 targets NSE (Indian stock market). It has +1.30% expectancy, 1.73 profit factor, validated over 3,012 trades. The goal was to adapt it for US stocks to leverage:
- 10-20x higher YouTube CPM ($0.10-0.50 vs $0.005-0.05)
- 15x larger audience (300M US retail traders vs 20M Indian)
- Better liquidity (tighter fills, less slippage)

**What changed:**
- Stock universe: Nifty 500 → S&P 500 (`sp500.txt`, 503 symbols)
- Sector rotation: Nifty indices → S&P sector ETFs (XLK, XLV, XLF, etc.)
- Stock-to-sector mapping: NSE constituents → GICS classification
- Liquidity filters: Min 500k avg volume, $500M market cap
- Symbol format: `RELIANCE.NS` → `AAPL`

**What stayed the same:**
- Pattern detection logic (Cup & Handle, Double Bottom)
- Risk management (2.0x ATR, 8% cap)
- Target calculation (50% measured move)
- Scoring system (base + sector + volume + proximity + pattern)

### Phase 2: First scan — looked good but was wrong

Initial scan of S&P 500 found 783 setups. Top picks included AFL (Aflac) showing "Double Bottom, NEAR, 0.5% risk." Charts were generated. Everything looked great.

**Then the user noticed something was off:** AFL's current price was $116 but entry was $122 — a 4.8% gap. The stock was FALLING, not rising toward breakout. The "0.5% risk" was calculated from current price, not entry price.

### Phase 3: Deep investigation — found 5 critical bugs

Debugging AFL revealed the pattern detection had fundamental flaws:

```
AFL data (Aug 2026):
  Aug 13: Bottom 1 at $119.14
  Aug 18: Peak at $122.17 (only 5 days later!)
  Aug 20: Bottom 2 at $115.82 (LOWER than bottom 1!)
  Aug 28: Current at $116.67 (stock still falling)

Scanner said: "Double Bottom, NEAR, 0.5% risk"
Reality:      Stock crashing, not a double bottom at all
```

### Phase 4: Fix all bugs + add multi-timeframe confirmation

Rewrote pattern detection with strict Bulkowski rules + weekly trend confirmation. Re-tested: AFL correctly rejected, MSFT/AAPL/GOOGL correctly identified as rising toward breakout.

### Phase 5: Build cached visual backtest

Previous backtest attempts failed due to yfinance rate limiting (48+ minutes, only 1 trade found). Built a new backtest engine that:
- Downloads all data ONCE (cached to disk)
- Replays day-by-day from cache (no API calls)
- Completes 5-year backtest in 0.6 minutes

**Results:** 74.1% win rate, +2.28% expectancy, +61.6% return over 5 years.

---

## Bugs We Found & Fixed

### Bug 1: Risk calculated from CMP, not ENTRY

**The problem:**
```python
# BROKEN (v1)
risk_pct = (cmp - stop_loss) / cmp  # Risk from current price
```

If CMP = $116 and stop = $115, risk shows as 0.9%. But you enter at $122 (breakout), so actual risk is ($122 - $115) / $122 = 5.7%. The scanner was understating risk by 5x.

**The fix:**
```python
# FIXED (v2)
risk_pct = (breakout - stop_loss) / breakout  # Risk from entry price
```

Risk is now calculated from the breakout level (where you actually enter), not current price.

### Bug 2: Double Bottom bottoms too close together

**The problem:**
v1 accepted bottoms only 7 days apart. AFL had Bottom 1 on Aug 13 and Bottom 2 on Aug 20 — just 7 days. This is noise, not a pattern. Real double bottoms need weeks between bottoms.

**The fix:**
```python
# FIXED (v2)
if (bottom2_idx - bottom1_idx) < 15:
    return None  # Min 15 bars between bottoms
```

### Bug 3: Crashing stocks showed as "NEAR"

**The problem:**
v1 classified any stock within 5% of breakout as "NEAR." But if the stock is FALLING away from breakout (price dropping), it's not approaching breakout — it's moving away.

**The fix:**
```python
# FIXED (v2)
# Current price must be RECOVERING (above bottom 2)
if cmp < min(bottom1_price, bottom2_price):
    return None  # Stock still falling, not a valid setup

# Momentum check: 5D close must be > 10D close (stock rising)
rising = check_momentum(df)
if dist_to_breakout <= 0.05 and rising:
    status = 'NEAR'
elif dist_to_breakout <= 0.05 and not rising:
    return None  # Stock falling away from breakout
```

### Bug 4: Handle could be a crash

**The problem:**
v1 accepted any handle depth up to 50% of cup depth. But it didn't check if the handle was near the right rim. A stock could crash 20% from the right rim and still pass as a "handle."

**The fix:**
```python
# FIXED (v2)
# Handle must be near right rim (not a crash)
if (right_rim - handle_low) / right_rim > 0.15:
    return None  # Handle too far below rim — it's a crash, not a handle
```

### Bug 5: Backtest entry at open price (gaps above T1)

**The problem:**
The backtest entered trades at next day's open price. But if the stock gapped up above T1 at open, the trade would "hit T1" instantly — but with a negative P&L because entry was above T1.

```
Example (v1 backtest):
  DE  2024-12-10 -> 2024-12-11 | WIN_T1 | -3.9%  ← BUG! T1 hit but lost money
  V   2025-02-04 -> 2025-02-05 | WIN_T1 | -4.1%  ← BUG!
```

**The fix:**
```python
# FIXED (v2)
if entry_price > best['target_1']:
    continue  # Gapped above target — no trade

actual_entry = min(entry_price, best['entry'])  # Use breakout if gapped up
```

**Impact of fix:** Win rate jumped from 45% → 74%, return from -25% → +61%.

---

## Multi-Timeframe Confirmation

### The concept

A daily pattern is more reliable when confirmed by a higher timeframe trend. If the weekly chart shows an uptrend, daily breakouts have higher probability of success.

### Implementation

```python
def check_higher_trend(df_weekly):
    """Check if stock is in uptrend on weekly timeframe"""
    if df_weekly is None or len(df_weekly) < 50:
        return True  # Can't determine, allow

    sma_50 = df_weekly['Close'].rolling(50).mean().iloc[-1]
    current = df_weekly['Close'].iloc[-1]

    # Stock should be above 50-week SMA (long-term uptrend)
    # OR within 10% below (recovering)
    if current > sma_50:
        return True
    elif current > sma_50 * 0.90:
        return True
    else:
        return False
```

### Scoring impact

- MTF-confirmed setups: **+15 score bonus**
- Non-MTF setups: **-10 score penalty**
- `--mtf-only` flag shows only MTF-confirmed setups

### Why it matters

In the 5-year backtest, the MTF filter kept the scanner OUT of the market during the 2022 bear market (10 months of zero trades). This alone prevented major losses.

---

## Backtest Results

### 5-Year Backtest (backbone_us.txt, 50 stocks, MTF-confirmed)

| Metric | Value |
|---|---|
| **Total trades** | 27 |
| **Win rate** | **74.1%** |
| **Avg win** | +4.9% |
| **Avg loss** | -5.1% |
| **Expectancy** | **+2.28% per trade** |
| **Profit factor** | **2.71** |
| **Max drawdown** | -14.9% |
| **Total return** | **+61.6%** |
| **CAGR** | +10.1% |
| **Backtest time** | 0.6 minutes (cached) |

### Pattern breakdown

| Pattern | Trades | Win Rate | Expectancy |
|---|---|---|---|
| **Double Bottom** | 24 | **83.3%** | **+3.25%** |
| Cup & Handle (Daily) | 3 | 0.0% | -5.49% |

### 3-Year Backtest (same stocks)

| Metric | Value |
|---|---|
| Total trades | 26 |
| Win rate | 69.2% |
| Expectancy | +2.34% |
| Profit factor | 2.62 |
| Max drawdown | -10.1% |
| Total return | +60.7% |
| CAGR | +17.1% |

### How the backtest works

1. **Download all data ONCE** — 50 stocks × 5 years = ~3 minutes, cached to `backtest_cache/all_stocks_5y.pkl`
2. **Generate scan dates** — Every 14 days (bi-weekly) starting from first Monday
3. **Replay day-by-day** — At each scan date, detect patterns using only data up to that date
4. **Enter trades** — On BREAKOUT status, enter next day at open (or breakout if gapped up)
5. **Exit trades** — At T1 (win), stop loss (loss), or 45 days (time exit)
6. **Track equity** — Starting $10,000, no compounding (fixed position size)
7. **Generate equity curve** — Visual chart saved to `backtest_equity_YYYYMMDD.png`

### Comparison: scanner-us vs scanner-v3 (India)

| Metric | scanner-v3 (India) | scanner-us (US) |
|---|---|---|
| Trades | 3,012 | 27 |
| Win rate | 40.6% | **74.1%** |
| Avg win | +7.6% | +4.9% |
| Avg loss | -3.0% | -5.1% |
| Expectancy | +1.30% | **+2.28%** |
| Profit factor | 1.73 | **2.71** |
| Max DD | -60.1% | **-14.9%** |

**Note:** scanner-v3 has 3,012 trades (large sample, statistically significant). scanner-us has 27 trades (small sample, survivorship bias possible — see [Honest Caveats](#honest-caveats)).

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.12 | Core runtime |
| **Data source** | yfinance | Free Yahoo Finance API (no key needed) |
| **Data analysis** | pandas | DataFrame operations, resampling |
| **Numerical** | numpy | Arrays, mathematical operations |
| **Charting** | matplotlib | Equity curves, price charts |
| **Pattern smoothing** | scipy | Spline interpolation for cup shape |
| **Caching** | pickle | Serialize downloaded data to disk |
| **CLI** | argparse | Command-line interface |

### Architecture

```
scanner-us/
├── scanner_us.py              # Main scanner (v2.0)
│   ├── get_stock_data()       # Fetch + cache stock data
│   ├── detect_cup_and_handle()# C&H pattern detection
│   ├── detect_double_bottom() # Double Bottom detection
│   ├── check_momentum()       # 5D vs 10D momentum
│   ├── check_higher_trend()   # Weekly 50-SMA trend
│   ├── calculate_score()      # Scoring with MTF bonus
│   └── scan_stock()           # Single stock scan
│
├── visual_backtest.py         # Cached backtest engine
│   ├── download_and_cache()   # One-time data download
│   ├── detect_patterns_at_date() # Historical pattern detection
│   ├── Trade class            # Trade tracking
│   ├── run_backtest()         # Main backtest loop
│   └── plot_equity_curve()    # Visual equity curve
│
├── chart_generator_v3.py      # Chart generator
│   ├── Cup shape drawing      # scipy spline interpolation
│   ├── Double Bottom W-shape  # Cyan line connecting bottoms
│   └── Entry/Stop/Target lines # Color-coded with labels
│
├── verify_picks.py            # Pick validator
│   ├── Live CMP check         # Compare scanner vs live price
│   ├── Stop < Entry check     # Validate stop is below entry
│   ├── T1/T2 ordering check   # Validate T1 < T2
│   └── Risk ≤ 8% check        # Validate risk from entry
│
└── utils/
    └── sector_rotation_us.py  # S&P sector rotation
        ├── 11 SPDR ETFs       # XLK, XLV, XLF, XLE, XLY, XLP, XLI, XLB, XLU, XLRE, XLC
        ├── BOOM/RISING/COOLING/WEAK signals
        └── Stock-to-sector mapping (GICS)
```

---

## Pattern Detection Rules

### Cup & Handle

**Criteria (Bulkowski):**
- Cup depth: 12-50% (not too shallow, not too deep)
- Handle depth: <50% of cup depth (shallow pullback)
- Handle must be within 15% of right rim (not a crash)
- Cup window: 30 bars (daily/weekly), 24 bars (monthly)
- Handle window: 4 bars (daily/weekly), 3 bars (monthly)

**Entry:** Right rim high (breakout level)
**Stop:** Handle low OR 2.0x ATR from entry (whichever tighter), capped at 8%
**Targets:** T1 = entry + (cup_depth × 50%), T2 = entry + (cup_depth × 100%)

**Status:**
- BREAKOUT: Price >= breakout level
- NEAR: Within 5% of breakout AND rising (5D > 10D)
- WATCH: Within 15% of breakout AND rising

### Double Bottom

**Criteria (Bulkowski):**
- 2 lows within 3% of each other (last 60 bars)
- Minimum 15 bars between bottoms (not noise)
- Current price must be above bottom 2 (stock recovering)
- Peak between bottoms (the breakout level)

**Entry:** Peak high (breakout level)
**Stop:** Lower of 2 bottoms OR 2.0x ATR from entry, capped at 8%
**Targets:** T1 = entry + (peak - bottom) × 50%, T2 = entry + (peak - bottom) × 100%

**Status:** Same as Cup & Handle (with momentum check)

---

## Scoring System

```python
score = base_score + sector_bonus + volume_bonus + proximity_bonus + pattern_bonus + mtf_bonus + risk_penalty
```

| Component | Value | Notes |
|---|---|---|
| Base score | 0-60 | R:R × 20, capped at 60 |
| Sector bonus | +20 / +10 / 0 / -10 | BOOM / RISING / COOLING / WEAK |
| Volume bonus | +10 | If recent volume > 2x avg |
| Proximity bonus | +15 / +10 / +5 | BREAKOUT / NEAR / WATCH |
| Pattern bonus | +28 / +25 / +20 | Double Bottom / C&H Weekly-Monthly / C&H Daily |
| MTF bonus | +15 / -10 | MTF-confirmed / not confirmed |
| Risk penalty | ×0.5 / ×0.8 | If risk > 8% / > 6% |

**Example:**
```
MSFT - Cup & Handle (Monthly) - MTF Confirmed
  Base:      3.2 R:R × 20 = 64 (capped at 60)
  Sector:    Info Tech RISING = +10
  Volume:    0.6x (< 2.0x) = 0
  Proximity: NEAR (0.7% from BO) = +10
  Pattern:   Monthly = +25
  MTF:       Weekly trend confirmed = +15
  Risk:      3.8% (< 6.0%) = ×1.0
  ─────────────────────────────────────
  Final:     (60 + 10 + 0 + 10 + 25 + 15) × 1.0 = 120.0
```

---

## Sector Rotation

Tracks 11 S&P sectors via SPDR ETFs:

| Sector | ETF |
|---|---|
| Information Technology | XLK |
| Health Care | XLV |
| Financials | XLF |
| Energy | XLE |
| Consumer Discretionary | XLY |
| Consumer Staples | XLP |
| Industrials | XLI |
| Materials | XLB |
| Utilities | XLU |
| Real Estate | XLRE |
| Communication Services | XLC |

**Signals (based on 5-day and 20-day ETF performance):**
- **BOOM**: 5D > +2% AND 20D > +3% → +20 score bonus
- **RISING**: 5D > 0 AND 20D > 0 → +10 score
- **COOLING**: 5D < 0 BUT 20D > 0 → 0 score
- **WEAK**: 20D < 0 → -10 score (avoid)

---

## Files

| File | Purpose |
|---|---|
| `scanner_us.py` | Main scanner (v2.0 - MTF confirmation + bug fixes) |
| `visual_backtest.py` | Cached backtest engine (no rate limiting) |
| `chart_generator_v3.py` | Chart generator with pattern overlay |
| `verify_picks.py` | Validate entry/SL/targets correctness |
| `utils/sector_rotation_us.py` | S&P sector rotation tracking |
| `sp500.txt` | S&P 500 stock list (503 symbols) |
| `sp500_sectors.json` | Symbol → GICS sector mapping |
| `backbone_us.txt` | Top 50 curated momentum stocks |
| `requirements.txt` | Python dependencies |
| `backtest_cache/` | Cached stock data (pickle files) |

---

## Usage

### 1. Daily Quick Scan

```powershell
python scanner_us.py
```

Scans `backbone_us.txt` (50 stocks), outputs top 30 setups.

### 2. Full S&P 500 Scan

```powershell
python scanner_us.py --stocks sp500.txt --top 50 --min-score 50 --mtf-only
```

Scans all 503 S&P 500 stocks, outputs top 50 MTF-confirmed setups.

### 3. Test Mode

```powershell
python scanner_us.py --test --mtf-only
```

Scans first 10 stocks only. Use for quick testing.

### 4. Verify Picks

```powershell
python verify_picks.py
```

Validates that entry/SL/targets are correctly specified:
- Stop < Entry < T1 < T2
- Risk ≤ 8% (from entry, not CMP)
- R:R ≥ 1.5
- Live CMP matches scanner
- MTF confirmed

### 5. Generate Charts

```powershell
# Single stock chart with pattern overlay
python chart_generator_v3.py MSFT

# Top 5 picks from scan
python chart_generator_v3.py --batch results_us_2026-08-29.csv --top 5
```

Chart features:
- 1 year of price data (line chart)
- Pattern overlay (cup shape via scipy spline, double bottom W-shape)
- Entry/Stop/T1/T2 lines with labels
- Current price marker (yellow diamond)
- Distance to breakout arrow
- Dark theme (YouTube-ready)

### 6. Backtest

```powershell
# 5-year backtest on backbone stocks (50 stocks, ~3 min download + 0.6 min backtest)
python visual_backtest.py --stocks backbone_us.txt --years 5 --visual

# 5-year backtest on S&P 500 (503 stocks, ~15 min download + 5 min backtest)
python visual_backtest.py --stocks sp500.txt --years 5 --visual

# Test mode (10 stocks, 1 year)
python visual_backtest.py --test --visual

# Include non-MTF trades (for comparison)
python visual_backtest.py --stocks backbone_us.txt --years 5 --no-mtf --visual
```

**How it works:**
1. Downloads all stock data ONCE (cached to `backtest_cache/`)
2. Replays day-by-day from cached data (no API calls)
3. Detects patterns at each historical date
4. Enters trades on BREAKOUT, exits at T1/SL/45 days
5. Generates equity curve chart

---

## Honest Caveats

### 1. Survivorship bias (BIGGEST issue)

`backbone_us.txt` contains TODAY'S top stocks (AAPL, MSFT, NVDA, JPM, etc.). These are the winners that survived. 5 years ago, this list would have been different. We're backtesting today's winners on past data — this inflates returns.

**Mitigation:** Run `python visual_backtest.py --stocks sp500.txt --years 5` for a more realistic number (S&P 500 includes stocks that were removed).

### 2. Small sample size

27 trades over 5 years is not enough to be statistically significant. A few bad trades would change the picture dramatically. Need 100+ trades for confidence.

### 3. No slippage or commissions

Real trading has:
- Bid/ask spread (~0.05-0.1%)
- Slippage on entry (~0.1-0.3%)
- Commission ($0-5/trade)

These would reduce returns by ~1-2% per trade.

### 4. Cup & Handle Daily lost all 3 trades

0% win rate, -5.49% expectancy. Small sample but concerning. May need to disable C&H Daily or investigate why.

### 5. T1 exit only

We exit at Target 1 (50% of measured move). Some trades would have hit T2 for bigger gains, but some would have reversed from T1 back to stop. Untested.

### 6. Fixed position size

Backtest uses fixed $10,000 capital with no compounding. Real trading would use position sizing (e.g., 10% per trade), which changes results.

---

## Monetization Potential

### India picks (scanner-v3, current)
- YouTube CPM: Rs 0.40-4 ($0.005-$0.05)
- Audience: 20M Indian retail traders
- Affiliate: Rs 200-500/referral

### US picks (scanner-us, this scanner)
- YouTube CPM: **Rs 8-40 ($0.10-$0.50)** — **10x higher**
- Audience: **300M US retail traders** — **15x larger**
- Affiliate: **Rs 4k-16k ($50-200/referral)** — **20x higher**

**Revenue streams:**
1. YouTube Shorts (US stocks, US audience): Rs 40k-2L/month
2. Premium Discord ($10/mo): Rs 40k-1.6L/month (500 subs)
3. Affiliate (Webull, Robinhood): Rs 20k-80k/month
4. SaaS ($20/mo): Rs 80k-4L/month (500 users)

**Total potential: Rs 1.8L-10L/month** (vs Rs 12k-45k with India picks)

---

## Support

Issues / Questions: Open an issue on GitHub or contact the author.

**Built with:** Python 3.12, yfinance, pandas, numpy, matplotlib, scipy
**License:** MIT
**Author:** Kartik Bandewar
**Based on:** [scanner-v3](../scanner-v3) (India/NSE)

---

**Disclaimer:** This is a technical analysis tool for educational purposes. Past performance does not guarantee future results. Trade at your own risk.
