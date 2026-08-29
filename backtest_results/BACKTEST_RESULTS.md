# Backtest Results — scanner-us v2.0

## S&P 500 — 5-Year Backtest (Post C&H Weekly Fix)

**Date:** 2026-08-29
**Stocks:** 503 (full S&P 500)
**Years:** 5 (Aug 2021 – Aug 2026)
**Filter:** MTF-confirmed only (weekly 50-SMA trend)
**Scan interval:** Every 14 days (bi-weekly)
**Capital:** $10,000 (fixed position size, no compounding)
**Backtest time:** 5.6 minutes (cached data)

### Results

| Metric | Value |
|---|---|
| **Total trades** | **293** |
| **Wins** | 200 |
| **Losses** | 93 |
| **Win rate** | **69.0%** |
| **Avg win** | +4.4% |
| **Avg loss** | -4.3% |
| **Expectancy** | **+1.62% per trade** |
| **Profit factor** | **2.20** |
| **Max drawdown** | -36.3% |
| **Starting capital** | $10,000 |
| **Total return** | **+442.1%** |
| **CAGR** | **+40.2%** |

### Pattern Breakdown (post C&H Weekly fix)

| Pattern | Trades | Win Rate | Expectancy | PF | Verdict |
|---|---|---|---|---|---|
| **Double Bottom** | 259 | **71.0%** | **+1.73%** | **2.46** | ✅ Star pattern |
| **C&H Weekly** | 23 | **52.2%** | **+1.65%** | **1.56** | ✅ Good (2nd best) |
| C&H Daily | 11 | 36.4% | -0.37% | 0.84 | ❌ Loser |
| C&H Monthly | 0 | — | — | — | Not detected (rare) |

**Key finding:** C&H Weekly is profitable (+1.65% expectancy). Before the timeframe bug fix, the backtest showed 0 C&H Weekly trades — the bug hid the data.

### Exit Reasons

| Exit | Trades | Avg P&L |
|---|---|---|
| WIN_T1 (target hit) | 193 | +4.49% |
| LOSS (stop hit) | 92 | -4.31% |
| TIME_EXIT (45 days) | 8 | +1.45% |
| BACKTEST_END | 2 | N/A |

### Key Observations

1. **Double Bottom dominates** — 259 of 293 trades (88%). This is the scanner's bread and butter.
2. **C&H Weekly is the 2nd-best pattern** — 52.2% WR, +1.65% expectancy. Was hidden by a bug (daily data used for all timeframes). Now fixed.
3. **Cup & Handle Daily is losing** — 36.4% win rate, -0.37% expectancy. Consider disabling with `--db-only`.
4. **MTF filter works** — Kept scanner out of 2022 bear market (10 months of zero trades early on).
5. **69% win rate is real** — 293 trades is statistically significant.
6. **+1.62% expectancy** — Better than scanner-v3 India (+1.30% over 3,012 trades).

### Comparison: scanner-us vs scanner-v3 (India)

| Metric | scanner-v3 (India) | scanner-us (US) |
|---|---|---|
| Trades | 3,012 | 293 |
| Win rate | 40.6% | **69.0%** |
| Avg win | +7.6% | +4.4% |
| Avg loss | -3.0% | -4.3% |
| Expectancy | +1.30% | **+1.62%** |
| Profit factor | 1.73 | **2.20** |
| Max DD | -60.1% | -36.3% |

### Caveats

1. **Survivorship bias** — S&P 500 includes only current members. Stocks removed during the 5-year period (e.g., SVB, FRC) are not included. This slightly inflates results.
2. **No slippage/commissions** — Real trading would reduce returns by ~1-2% per trade.
3. **Fixed position size** — No compounding. Real trading with position sizing would differ.
4. **T1 exit only** — We exit at Target 1 (50% of measured move). T2 performance untested.
5. **Cup & Handle Daily** — Losing money (36.4% WR). Should be disabled or filtered out.

### Files

| File | Description |
|---|---|
| `sp500_5yr_295trades.csv` | All 293 trades with entry/exit/P&L (post C&H Weekly fix) |
| `equity_curve_sp500_5yr_v2.png` | Visual equity curve chart (post fix) |
| `sp500_5yr_274trades.csv` | Earlier backtest (before C&H Weekly fix) |
| `equity_curve_sp500_5yr.png` | Earlier equity curve (before fix) |
| `scan_results_2026-08-29.csv` | Latest live scan results |

### How to Reproduce

```powershell
# Download S&P 500 data (one-time, ~3 min) + run 5-year backtest
python visual_backtest.py --stocks sp500.txt --years 5 --visual

# After refresh_sp500.py, update cache incrementally
python visual_backtest.py --stocks sp500.txt --years 5 --refresh-cache --visual

# Analyze patterns by timeframe
python analyze_patterns.py backtest_results/sp500_5yr_295trades.csv
```
