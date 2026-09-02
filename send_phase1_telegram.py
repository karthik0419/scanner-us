"""Send Phase 1 optimization results to Telegram."""
from telegram_helper import send_message

msg = """PHASE 1: TRADE PROFITABILITY OPTIMIZATION
=========================================

Tested 6 SL methods x 6 targets x 3 hold periods
= 108 combinations on 1,726 sampled trades

CURRENT CONFIG: ATR 2x | 50% measured move | 45-day exit
Current results: 65.8% WR | +2.64% exp | PF 2.99

=========================================
TEST 1: STOP LOSS METHODS
=========================================
Method      WR      Exp      PF    AvgWin  AvgLoss
atr_1.5x   63.5%  +2.69%   3.44   +5.97%  -3.02%
atr_2x     65.8%  +2.64%   2.99   +6.02%  -3.89%  (current)
atr_2.5x   68.1%  +2.64%   2.77   +6.06%  -4.69%
fixed_5    69.6%  +2.67%   2.75   +6.02%  -5.03%
fixed_8    74.8%  +2.64%   2.42   +6.01%  -7.44%
fixed_10   76.8%  +2.65%   2.34   +6.01%  -8.68%

KEY: Tighter stops = higher PF!
ATR 1.5x has best PF (3.44) with similar expectancy.
Wider stops increase WR but decrease PF (bigger losses).

=========================================
TEST 2: TARGET METHODS
=========================================
Method      WR      Exp      PF    AvgWin  AvgLoss
pct25      82.4%  +1.81%   3.84   +2.97%  -3.64%
pct50      65.8%  +2.64%   2.99   +6.02%  -3.89%  (current)
pct75      52.4%  +2.74%   2.50   +8.67%  -3.86%
pct100     47.2%  +3.05%   2.51  +10.65%  -3.85%
rr_2       59.8%  +2.35%   2.44   +6.62%  -4.06%
rr_3       52.3%  +2.74%   2.41   +8.91%  -4.10%

KEY: Lower target = higher WR + higher PF
pct25 (25% of measured move) = 82% WR, PF 3.84
But expectancy drops to +1.81% (vs +2.64%)
pct100 (full move) = best expectancy +3.05% but only 47% WR

Tradeoff: Quick small wins (pct25) vs slow big wins (pct100)

=========================================
TEST 3: MAX HOLD PERIOD
=========================================
Days     WR      Exp      PF
20d     66.6%  +2.58%   3.06
30d     66.4%  +2.63%   3.04
45d     65.8%  +2.64%   2.99  (current)
60d     65.8%  +2.65%   2.99
90d     65.7%  +2.64%   2.98

KEY: Hold period barely matters!
Most trades exit within 10 days anyway (avg hold 10.2d).
20-day exit is slightly better PF (3.06 vs 2.99).
Can reduce to 30 days with minimal impact.

=========================================
TEST 4: BEST COMBINATIONS (top 5 by PF)
=========================================
SL        Target   Hold    WR      Exp     PF
atr_1.5x  pct25    45d   80.6%  +1.84%  4.37
atr_2x    pct25    45d   82.4%  +1.81%  3.84
fixed_5   pct25    45d   84.9%  +1.80%  3.48
atr_1.5x  pct50    30d   64.0%  +2.68%  3.47
atr_1.5x  pct50    45d   63.5%  +2.69%  3.44

BEST PF: atr_1.5x + pct25 + 45d = PF 4.37
BEST EXP: atr_1.5x + pct50 + 45d = +2.69% exp, PF 3.44

=========================================
TEST 5: BEST COMBO PER PATTERN
=========================================
(Using atr_1.5x + pct25 + 45d)

Falling Wedge (1,080 trades):
  80.7% WR | +1.90% exp | PF 4.70

Inverse H&S (232 trades):
  87.1% WR | +2.05% exp | PF 6.02

Channel BO (190 trades):
  76.3% WR | +1.97% exp | PF 3.79

Asc Triangle (118 trades):
  73.7% WR | +1.19% exp | PF 2.69

Double Bottom (62 trades):
  83.9% WR | +1.23% exp | PF 3.23

Double Top BO (36 trades):
  80.6% WR | +1.28% exp | PF 3.20

C&H Weekly (8 trades):
  50.0% WR | +0.57% exp | PF 1.23
  (too few trades — inconclusive)

=========================================
KEY FINDINGS
=========================================

1. TIGHTER STOPS ARE BETTER
   ATR 1.5x beats ATR 2.0x on PF (3.44 vs 2.99)
   Smaller losses when wrong = higher profit factor
   Current 2.0x ATR is too wide

2. LOWER TARGETS = HIGHER WIN RATE
   25% of measured move: 82% WR, PF 3.84
   50% (current): 66% WR, PF 2.99
   100% (full move): 47% WR, PF 2.51
   Quick exits capture more wins but smaller profits

3. HOLD PERIOD BARELY MATTERS
   Most trades resolve in ~10 days
   Can reduce from 45 to 30 days with minimal impact

4. TWO VIABLE STRATEGIES:
   A) Quick scalps: ATR 1.5x + 25% target
      81% WR | +1.84% exp | PF 4.37 | 3-day avg hold
      High win rate, fast turnover, small wins

   B) Swing trades: ATR 1.5x + 50% target
      64% WR | +2.69% exp | PF 3.44 | 9-day avg hold
      Lower win rate, bigger wins, higher expectancy

5. BEST PATTERN: Inverse H&S
   With optimized params: 87% WR, PF 6.02
   This is exceptional — nearly 9 out of 10 trades win!

=========================================
RECOMMENDATION
=========================================

Option A (Conservative): ATR 1.5x + 25% target + 30-day exit
  - 81% WR, PF 4.37, +1.84% exp
  - Best for small accounts, fast turnover
  - Lower drawdowns (small losses)

Option B (Balanced): ATR 1.5x + 50% target + 30-day exit
  - 64% WR, PF 3.47, +2.68% exp
  - Best expectancy while keeping PF > 3
  - Recommended for most traders

Option C (Aggressive): ATR 2.0x + 100% target + 45-day exit
  - 47% WR, PF 2.51, +3.05% exp
  - Highest expectancy but lower win rate
  - Bigger drawdowns, needs stronger psychology

MY PICK: Option B (ATR 1.5x + 50% target + 30 days)
  - PF improves from 2.99 to 3.47 (+16%)
  - Expectancy improves from +2.64% to +2.68%
  - Win rate drops slightly (66% to 64%)
  - Avg hold drops from 10 to 9 days
  - Best balance of profitability and consistency

Next: Update scanner_us.py with optimized params + re-run full backtest

GitHub: https://github.com/karthik0419/scanner-us"""

print("Sending Phase 1 results to Telegram...")
send_message(msg)
print("Done!")
