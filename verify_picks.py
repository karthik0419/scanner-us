"""Verify scanner picks - check entry/SL/targets are correct per pattern rules"""
from scanner_us import scan_stock
import yfinance as yf
import json

stocks = ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'META', 'QCOM']

for symbol in stocks:
    print('='*70)
    print(f'{symbol} - Verification')
    print('='*70)

    results = scan_stock(symbol)
    mtf_results = [r for r in results if r.get('mtf_confirmed')]

    if not mtf_results:
        print('  No MTF-confirmed setups')
        print()
        continue

    # Show best setup
    best = max(mtf_results, key=lambda x: x['score'])
    print(f'  Pattern: {best["pattern"]}')
    print(f'  Status: {best["status"]}')
    print(f'  Sector: {best["sector"]}')
    print(f'  MTF Confirmed: {best["mtf_confirmed"]}')
    print()
    print(f'  CMP (current):   ${best["cmp"]:.2f}')
    print(f'  Entry (breakout):${best["entry"]:.2f}')
    print(f'  Stop Loss:       ${best["stop_loss"]:.2f}')
    print(f'  Target 1:        ${best["target_1"]:.2f}')
    print(f'  Target 2:        ${best["target_2"]:.2f}')
    print()
    print(f'  Risk (from entry): {best["risk_pct"]:.1f}%')
    print(f'  Upside to T1:      {best["upside_pct"]:.1f}%')
    print(f'  R:R:               {best["rr"]:.1f}x')
    print(f'  Distance to BO:    {best["dist_to_breakout_pct"]:.1f}%')
    print(f'  Score:             {best["score"]}')
    print()

    # VERIFY: Fetch live data and check
    df = yf.Ticker(symbol).history(period='1y', auto_adjust=True)
    cmp = df['Close'].iloc[-1]
    high_30d = df['High'].iloc[-30:].max()
    low_30d = df['Low'].iloc[-30:].min()

    print(f'  LIVE DATA CHECK:')
    print(f'    Live CMP:        ${cmp:.2f} (scanner: ${best["cmp"]:.2f})')
    print(f'    30D High:        ${high_30d:.2f} (entry should be near this)')
    print(f'    30D Low:         ${low_30d:.2f}')
    print()

    # VERIFY: Entry should be at/near recent high (breakout level)
    entry_diff = abs(best['entry'] - high_30d) / high_30d * 100
    print(f'  VALIDATION:')
    print(f'    Entry vs 30D High: {entry_diff:.1f}% diff (should be <5%)')
    print(f'    Stop < Entry: {"YES" if best["stop_loss"] < best["entry"] else "NO - BUG!"}')
    print(f'    T1 > Entry: {"YES" if best["target_1"] > best["entry"] else "NO - BUG!"}')
    print(f'    T2 > T1: {"YES" if best["target_2"] > best["target_1"] else "NO - BUG!"}')
    print(f'    Risk <= 8%: {"YES" if best["risk_pct"] <= 8.0 else "NO - BUG!"}')
    print(f'    R:R >= 1.5: {"YES" if best["rr"] >= 1.5 else "LOW R:R"}')
    print()
