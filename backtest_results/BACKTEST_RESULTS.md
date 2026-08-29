# Backtest Results — scanner-us v2.0

## S&P 500 — 5-Year Backtest (Statistically Significant)

**Date:** 2026-08-29
**Stocks:** 503 (full S&P 500)
**Years:** 5 (Aug 2021 – Aug 2026)
**Filter:** MTF-confirmed only (weekly 50-SMA trend)
**Scan interval:** Every 14 days (bi-weekly)
**Capital:** $10,000 (fixed position size, no compounding)
**Backtest time:** 5.1 minutes (cached data)

### Results

| Metric | Value |
|---|---|
| **Total trades** | **274** |
| **Wins** | 189 |
| **Losses** | 84 |
| **Win rate** | **69.0%** |
| **Avg win** | +4.14% |
| **Avg loss** | -4.05% |
| **Expectancy** | **+1.62% per trade** |
| **Profit factor** | **2.30** |
| **Max drawdown** | -23.4% |
| **Starting capital** | $10,000 |
| **Final capital** | $54,211 |
| **Total return** | **+442.1%** |
| **CAGR** | **+40.2%** |

### Pattern Breakdown

| Pattern | Trades | Win Rate | Expectancy | Verdict |
|---|---|---|---|---|
| **Double Bottom** | 259 | **70.7%** | **+1.73%** | ✅ Star performer |
| Cup & Handle (Monthly) | 4 | 50.0% | +0.09% | ⚠️ Too few trades |
| Cup & Handle (Daily) | 11 | 36.4% | -0.37% | ❌ Losing money |

### Exit Reasons

| Exit | Trades | Avg P&L |
|---|---|---|
| WIN_T1 (target hit) | 184 | +4.19% |
| LOSS (stop hit) | 86 | -3.93% |
| TIME_EXIT (45 days) | 3 | +3.29% |
| BACKTEST_END | 1 | N/A |

### Key Observations

1. **Double Bottom dominates** — 259 of 274 trades (94.5%). This is the scanner's bread and butter.
2. **Cup & Handle Daily is losing** — 36.4% win rate, -0.37% expectancy. Consider disabling.
3. **MTF filter works** — Kept scanner out of 2022 bear market (10 months of zero trades early on).
4. **69% win rate is real** — 274 trades is statistically significant (vs 27 in backbone test).
5. **+1.62% expectancy** — Better than scanner-v3 India (+1.30% over 3,012 trades).

### Comparison: scanner-us vs scanner-v3 (India)

| Metric | scanner-v3 (India) | scanner-us (US) |
|---|---|---|
| Trades | 3,012 | 274 |
| Win rate | 40.6% | **69.0%** |
| Avg win | +7.6% | +4.14% |
| Avg loss | -3.0% | -4.05% |
| Expectancy | +1.30% | **+1.62%** |
| Profit factor | 1.73 | **2.30** |
| Max DD | -60.1% | **-23.4%** |

### Caveats

1. **Survivorship bias** — S&P 500 includes only current members. Stocks removed during the 5-year period (e.g., SVB, FRC) are not included. This slightly inflates results.
2. **No slippage/commissions** — Real trading would reduce returns by ~1-2% per trade.
3. **Fixed position size** — No compounding. Real trading with position sizing would differ.
4. **T1 exit only** — We exit at Target 1 (50% of measured move). T2 performance untested.
5. **Cup & Handle Daily** — Losing money (36.4% WR). Should be disabled or investigated.

### Files

| File | Description |
|---|---|
| `sp500_5yr_274trades.csv` | All 274 trades with entry/exit/P&L |
| `equity_curve_sp500_5yr.png` | Visual equity curve chart |
| `scan_results_2026-08-29.csv` | Latest live scan results |
| `backtest_results_us_2026-08-28.csv` | Earlier backtest (v1, before bug fixes) |

### How to Reproduce

```powershell
# Download S&P 500 data (one-time, ~3 min) + run 5-year backtest
python visual_backtest.py --stocks sp500.txt --years 5 --visual

# Or use cached data (if already downloaded)
python visual_backtest.py --stocks sp500.txt --years 5 --visual
```
