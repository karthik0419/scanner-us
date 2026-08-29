@echo off
title Scanner-US - Weekly S&P 500 Scan
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo  ================================================================
echo   SCANNER-US - Weekly S&P 500 Scan (MTF only)
echo  ================================================================
echo.
echo  Scanning all 503 S&P 500 stocks for swing setups.
echo  Only shows MTF-confirmed setups (weekly trend aligned).
echo  Estimated time: ~10 minutes.
echo.
echo  Press any key to start...
pause >nul

python scanner_us.py --stocks sp500.txt --top 50 --min-score 50 --mtf-only

echo.
echo  ================================================================
echo  Scan complete. Results saved to results_us_*.csv
echo  ================================================================
echo.
pause
