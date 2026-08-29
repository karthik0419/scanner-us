@echo off
title Scanner-US - Backtest
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo  ================================================================
echo   SCANNER-US - Backtest Menu
echo  ================================================================
echo.
echo   1. Backbone 50, 3 years (~3 min)
echo   2. Backbone 50, 5 years (~3 min)
echo   3. Full S&P 500, 5 years (~15 min)
echo   4. Test mode (10 stocks, 1 year, fast)
echo   5. Back to main menu
echo.
set /p choice="  Enter choice [1-5]: "

if "%choice%"=="1" python visual_backtest.py --stocks backbone_us.txt --years 3 --visual
if "%choice%"=="2" python visual_backtest.py --stocks backbone_us.txt --years 5 --visual
if "%choice%"=="3" python visual_backtest.py --stocks sp500.txt --years 5 --visual
if "%choice%"=="4" python visual_backtest.py --test --years 1 --visual
if "%choice%"=="5" exit /b 0
echo.
echo  Results saved to backtest_results\ folder.
pause
