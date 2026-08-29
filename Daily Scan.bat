@echo off
title Scanner-US - Quick Daily Scan
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo  ================================================================
echo   SCANNER-US - Quick Daily Scan (Backbone 50, MTF only)
echo  ================================================================
echo.
echo  Scanning 50 high-momentum US stocks for swing setups.
echo  Only shows MTF-confirmed setups (weekly trend aligned).
echo  Estimated time: ~2 minutes.
echo.
echo  Press any key to start...
pause >nul

python scanner_us.py --top 30 --mtf-only

echo.
echo  ================================================================
echo  Scan complete. Results saved to results_us_*.csv
echo  ================================================================
echo.
pause
