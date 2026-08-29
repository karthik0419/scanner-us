"""Send $1000 simulation results to Telegram."""
import requests

TOKEN = "TELEGRAM_BOT_TOKEN_REDACTED"
CHAT_ID = "TELEGRAM_CHAT_ID_REDACTED"


def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    chunks = []
    current = ""
    for line in msg.split("\n"):
        if len(current) + len(line) + 1 > 4000:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    for chunk in chunks:
        resp = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        print(f"  Sent ({len(chunk)} chars): {'OK' if resp.ok else 'FAIL'}")


msg = """💰 <b>$1,000 FOR 1 YEAR — PROFIT SIMULATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Setup:</b> $1,000 starting capital, 1 year (Aug 2025 - Aug 2026)
Using actual backtest trades from 10-pattern scanner

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>1-YEAR STATS (all patterns)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total trades available: <b>1,111</b>
• Win rate: <b>64.8%</b> (720W / 391L)
• Avg win: +6.8% | Avg loss: -3.4%
• Avg expectancy: <b>+3.22% per trade</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 <b>4 SCENARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>1. Theoretical max (unlimited capital)</b>
   Take ALL 1,111 trades
   Return: <b>+3,580%</b> ($35,800 profit)
   ❌ Not realistic — need unlimited money

<b>2. Realistic — max 3 positions</b>
   $333 per trade, compounding
   Trades taken: 49 (out of 1,111)
   Final: <b>$1,534</b> | Profit: <b>+$534</b>
   Return: <b>+53.4%</b>

<b>3. Better — max 5 positions</b>
   $200 per trade, compounding
   Trades taken: 86 (out of 1,111)
   Final: <b>$1,763</b> | Profit: <b>+$763</b>
   Return: <b>+76.3%</b>

<b>4. Top patterns only — max 3</b>
   Only winning patterns, $333 each
   Trades taken: 49
   Final: <b>$1,534</b> | Profit: <b>+$534</b>
   Return: <b>+53.4%</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>BEST 1-YEAR PATTERNS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 <b>Double Top Breakout</b>
   24 trades | 87.5% WR | +4.39% exp
   (incredible in last year!)

🥈 <b>Channel Breakout</b>
   92 trades | 72.8% WR | +4.26% exp

🥉 <b>Falling Wedge</b>
   748 trades | 64.4% WR | +3.52% exp
   (most trades by far)

4. <b>Inverse Head & Shoulders</b>
   109 trades | 67.0% WR | +2.36% exp

5. <b>Double Bottom</b>
   32 trades | 68.8% WR | +1.49% exp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>REALITY CHECK</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These are <b>BACKTEST</b> results. Real-world:

📉 <b>Fees + slippage:</b> ~1-2% per trade
   With 86 trades x 1.5% = $129 in fees
   Scenario 3 real profit: ~$634 (not $763)

📊 <b>Survivorship bias:</b> S&P 500 only
   includes current members. Stocks that
   went bankrupt (SVB, FRC) are excluded.

⏰ <b>Timing:</b> You can't catch every trade.
   Realistically you'd take 50-70% of signals.

📈 <b>Last year was bullish:</b> 2025-2026
   was a strong market. In a bear year,
   returns would be much lower (MTF filter
   helps but doesn't eliminate risk).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <b>BOTTOM LINE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

With <b>$1,000</b> and max 5 positions:
• Backtest says: <b>+$763 (76% return)</b>
• Realistic (after fees): <b>~+$634 (63%)</b>
• Conservative (miss some trades): <b>~+$400-500</b>

With <b>$10,000</b> (same % returns):
• Backtest: <b>+$7,632</b>
• Realistic: <b>~+$6,300</b>

Compare to S&P 500 buy-and-hold:
• Last 1 year: ~+20% = $200 on $1,000
• Scanner: ~+63% = $630 on $1,000
• <b>3x better than buy-and-hold</b> (but higher risk)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Based on 5,659-trade backtest
S&P 500 | 10 patterns | 2025-2026
Past performance ≠ future results</i>"""

print("Sending to Telegram...")
send(msg)
print("Done!")
