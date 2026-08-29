@echo off
title Scanner-US v2.0 - Main Menu
cd /d "%~dp0"
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:MENU
cls
echo.
echo  ================================================================
echo                SCANNER-US v2.0 - US STOCK SCANNER
echo  ================================================================
echo.
echo   --- Scans ---
echo   1.  Quick scan - Backbone 50 stocks (~2 min, MTF only)
echo   2.  Full S&P 500 scan (~10 min, MTF only)
echo   3.  Full S&P 500 scan - ALL setups (incl. non-MTF)
echo   4.  Test mode - 10 stocks only (fast, ~30 sec)
echo   5.  Custom stock list scan
echo.
echo   --- Backtest ---
echo   6.  Backtest - Backbone 50, 3 years (~3 min)
echo   7.  Backtest - Backbone 50, 5 years (~3 min)
echo   8.  Backtest - Full S&P 500, 5 years (~15 min)
echo   9.  Backtest - Test mode (10 stocks, 1 year, fast)
echo.
echo   --- Charts ---
echo  10.  Generate chart for single stock
echo  11.  Generate charts for top 5 picks from latest scan
echo.
echo   --- Validation ---
echo  12.  Verify picks (validate entry/SL/targets)
echo  13.  Sector rotation heatmap
echo.
echo  14.  Exit
echo.
set /p choice="  Enter choice [1-14]: "

if "%choice%"=="1" goto SCAN_BACKBONE
if "%choice%"=="2" goto SCAN_SP500
if "%choice%"=="3" goto SCAN_SP500_ALL
if "%choice%"=="4" goto SCAN_TEST
if "%choice%"=="5" goto SCAN_CUSTOM
if "%choice%"=="6" goto BT_BACKBONE_3
if "%choice%"=="7" goto BT_BACKBONE_5
if "%choice%"=="8" goto BT_SP500_5
if "%choice%"=="9" goto BT_TEST
if "%choice%"=="10" goto CHART_SINGLE
if "%choice%"=="11" goto CHART_BATCH
if "%choice%"=="12" goto VERIFY
if "%choice%"=="13" goto SECTOR_HEAT
if "%choice%"=="14" exit /b 0
echo  Invalid choice.
pause
goto MENU

:SCAN_BACKBONE
cls
echo  === QUICK SCAN - Backbone 50 (MTF only, ~2 min) ===
echo.
python scanner_us.py --top 30 --mtf-only
pause
goto MENU

:SCAN_SP500
cls
echo  === FULL S&P 500 SCAN (MTF only, ~10 min) ===
echo.
python scanner_us.py --stocks sp500.txt --top 50 --min-score 50 --mtf-only
pause
goto MENU

:SCAN_SP500_ALL
cls
echo  === FULL S&P 500 SCAN - ALL setups (incl. non-MTF, ~10 min) ===
echo.
python scanner_us.py --stocks sp500.txt --top 50 --min-score 50
pause
goto MENU

:SCAN_TEST
cls
echo  === TEST MODE - 10 stocks (~30 sec) ===
echo.
python scanner_us.py --test --mtf-only
pause
goto MENU

:SCAN_CUSTOM
cls
echo  === CUSTOM STOCK LIST SCAN ===
echo  Available: backbone_us.txt, sp500.txt
echo.
set /p stockfile="  Enter stock list file: "
if "%stockfile%"=="" goto MENU
set /p topn="  Show top N [default 30]: "
if "%topn%"=="" set topn=30
python scanner_us.py --stocks "%stockfile%" --top %topn% --mtf-only
pause
goto MENU

:BT_BACKBONE_3
cls
echo  === BACKTEST - Backbone 50, 3 years (~3 min) ===
echo  Downloads data once (cached), then runs backtest.
echo.
python visual_backtest.py --stocks backbone_us.txt --years 3 --visual
echo.
echo  Results saved to backtest_results\ folder.
pause
goto MENU

:BT_BACKBONE_5
cls
echo  === BACKTEST - Backbone 50, 5 years (~3 min) ===
echo  Downloads data once (cached), then runs backtest.
echo.
python visual_backtest.py --stocks backbone_us.txt --years 5 --visual
echo.
echo  Results saved to backtest_results\ folder.
pause
goto MENU

:BT_SP500_5
cls
echo  === BACKTEST - Full S&P 500, 5 years (~15 min) ===
echo  Downloads 503 stocks (one-time, ~3 min), then backtests (~5 min).
echo.
python visual_backtest.py --stocks sp500.txt --years 5 --visual
echo.
echo  Results saved to backtest_results\ folder.
pause
goto MENU

:BT_TEST
cls
echo  === BACKTEST - Test mode (10 stocks, 1 year, fast) ===
echo.
python visual_backtest.py --test --years 1 --visual
pause
goto MENU

:CHART_SINGLE
cls
echo  === GENERATE CHART - Single Stock ===
echo  Draws pattern overlay (Cup and Handle / Double Bottom) on 1-year chart.
echo.
set /p symbol="  Enter stock symbol (e.g. MSFT, AAPL, NVDA): "
if "%symbol%"=="" goto MENU
python chart_generator_v3.py %symbol%
echo.
echo  Chart saved to current folder.
pause
goto MENU

:CHART_BATCH
cls
echo  === GENERATE CHARTS - Top 5 from Latest Scan ===
echo.
for /f "delims=" %%f in ('dir /b /o-d results_us_*.csv 2^>nul ^| findstr /r "results_us_.*\.csv"') do (
    set LATEST=%%f
    goto FOUND
)
:FOUND
if "%LATEST%"=="" (
    echo  No scan results found. Run a scan first.
    pause
    goto MENU
)
echo  Using latest scan: %LATEST%
echo.
python chart_generator_v3.py --batch %LATEST% --top 5
echo.
echo  Charts saved to charts_v3\ folder.
pause
goto MENU

:VERIFY
cls
echo  === VERIFY PICKS ===
echo  Validates entry/SL/targets from latest scan:
echo    - Stop ^< Entry ^< T1 ^< T2
echo    - Risk ^<= 8%% (from entry, not CMP)
echo    - R:R ^>= 1.5
echo    - Live CMP matches scanner
echo    - MTF confirmed
echo.
python verify_picks.py
pause
goto MENU

:SECTOR_HEAT
cls
echo  === SECTOR ROTATION HEATMAP ===
echo  Tracks 11 S&P sectors via SPDR ETFs (XLK, XLV, XLF, etc.)
echo.
python -c "from utils.sector_rotation_us import print_sector_heatmap; print_sector_heatmap()"
pause
goto MENU
