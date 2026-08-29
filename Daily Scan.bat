@echo off
title Scanner-US - Daily Scan (S&P 500, MTF only)
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo  ================================================================
echo   SCANNER-US - Daily Scan (S&P 500, MTF only)
echo  ================================================================
echo.
echo  Scans all 503 S&P 500 stocks for swing setups.
echo  Auto-refreshes stock list from Wikipedia (picks up new listings).
echo  Only shows MTF-confirmed setups (weekly trend aligned).
echo  Estimated time: ~10 minutes.
echo.
echo  Press any key to start...
pause >nul

python scanner_us.py --top 30 --mtf-only --best-only

echo.
echo  ================================================================
echo  Scan complete. Results saved to results_us_*.csv
echo  ================================================================
echo.
pause
