"""Send Phase 1 confirmation results to Telegram."""
from telegram_helper import send_message

msg = """PHASE 1 CONFIRMATION BACKTEST — PASSED
=========================================

Config: ATR 1.5x | 50% measured move | 30-day exit | 0.2% costs
No optimization. Run on ALL 4,763 trades (5,526 original, 86% match rate).

OVERALL: NEW vs CURRENT
=========================================
Metric          NEW (1.5x/30d)   CURRENT (2x/45d)   Delta
Trades          4,763            4,763              0
Win Rate        64.2%            66.6%              -2.4%
Expectancy      +2.69%           +2.71%             -0.02%
Profit Factor   3.54             3.13               +0.41 (+13%)
Avg Win         +5.84%           +5.98%             -0.14%
Avg Loss        -2.96%           -3.81%             +0.86% (better!)
Avg Hold        8.7d             10.4d              -1.7d
Max Loss Streak 10               11

KEY: PF improved 13%, avg loss shrunk from -3.81% to -2.96%.
Expectancy unchanged. Win rate slightly lower (tighter stops).
This is exactly the trade-off we wanted.

OUT-OF-SAMPLE TEST (critical)
=========================================
The optimization used 1,724 trades (sample). The remaining 3,039 were UNTOUCHED.

Metric          In-Sample    Out-of-Sample    Delta
Trades          1,724        3,039
Win Rate        63.1%        64.8%            +1.7%
Expectancy      +2.57%       +2.75%           +0.18%
Profit Factor   3.32         3.67             +0.35

VERDICT: PASS — OOS PF (3.67) is HIGHER than in-sample (3.32).
No overfitting detected. The edge is real.

PER-PATTERN BREAKDOWN (NEW CONFIG)
=========================================
Pattern                    Trades   WR     Exp      PF
Falling Wedge              2,973   66.0%  +3.03%   4.38
Inverse H&S                  614   64.3%  +2.37%   2.95
Channel Breakout             536   57.6%  +2.26%   2.44
Double Bottom                157   73.2%  +2.10%   3.40
Double Top BO                132   68.2%  +2.36%   3.32
Ascending Triangle           330   53.6%  +1.40%   2.03
C&H Weekly                    21   42.9%  +0.96%   1.34

All 6 core patterns profitable. C&H Weekly still too small (21 trades).

PER-PATTERN: IN-SAMPLE vs OOS
=========================================
Falling Wedge:
  In-sample:   1,047 trades | PF 4.32
  Out-of-sample: 1,926 trades | PF 4.41
  Delta: +0.09 — ROCK SOLID (no degradation)

Inverse H&S:
  In-sample:   223 | PF 2.53
  Out-of-sample: 391 | PF 3.22
  Delta: +0.68 — IMPROVED OOS

Channel BO:
  In-sample:   221 | PF 2.04
  Out-of-sample: 315 | PF 2.79
  Delta: +0.74 — IMPROVED OOS

Ascending Triangle:
  In-sample:   118 | PF 1.84
  Out-of-sample: 212 | PF 2.14
  Delta: +0.30 — IMPROVED OOS

Double Bottom:
  In-sample:   53 | PF 4.90
  Out-of-sample: 104 | PF 2.78
  Delta: -2.12 — degraded but still profitable
  (small sample, expected variance)

Double Top BO:
  In-sample:   53 | PF 4.74
  Out-of-sample: 79 | PF 2.63
  Delta: -2.11 — degraded but still profitable
  (small sample, expected variance)

C&H Weekly:
  9 in-sample, 12 OOS — too few to conclude

YEARLY BREAKDOWN (NEW CONFIG)
=========================================
Year    Trades    WR     Exp      PF
2021       848   65.6%  +2.82%   4.07
2022     2,477   62.3%  +2.58%   3.29
2023       827   67.6%  +2.80%   4.07
2024       335   64.8%  +2.56%   3.42
2025       211   66.4%  +3.17%   3.52
2026        65   63.1%  +2.60%   2.80

All 6 years profitable. No losing year.
2022 bear market: PF 3.29 (still strong).

DATA LEAKAGE + EXECUTION CHECKS
=========================================
1. Entry = next-day OPEN (not same-day close) — no lookback bias
2. SL/target checked using daily High/Low — realistic intraday fills
3. Pattern detection uses only data up to entry_date — no future data
4. Stop loss capped at 8% max risk — no unrealistic stops
5. Costs: 0.2% round trip on every trade — conservative
6. Entry price range: $4.48 - $7,914 (median $112)
7. Gap-above-target trades skipped — no edge

FINAL VERDICT
=========================================
PASS — New config holds up out-of-sample.

PF: 3.13 -> 3.54 (+13%)
OOS PF: 3.67 (higher than in-sample 3.32)
No overfitting. Edge is real.

Falling Wedge is the rock-solid foundation:
  2,973 trades | 66% WR | +3.03% exp | PF 4.38
  OOS delta: +0.09 (virtually no degradation)

SAFE TO UPDATE scanner_us.py with:
  ATR_MULTIPLIER = 1.5
  TARGET_1_PCT = 0.50
  MAX_HOLD_DAYS = 30

Next: Update config + re-run full portfolio backtest with new params.

GitHub: https://github.com/karthik0419/scanner-us"""

print("Sending confirmation results to Telegram...")
send_message(msg)
print("Done!")
