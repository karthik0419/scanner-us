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
echo   --- Smart Scans (filtered for quality) ---
echo   6.  Best setups only - 1 per stock, no duplicates (MTF)
echo   7.  Double Bottom only - the 70.7%% WR pattern (MTF)
echo   8.  Best + Double Bottom - highest quality (MTF)
echo.
echo   --- Backtest ---
echo   9.  Backtest - Backbone 50, 3 years (~3 min)
echo  10.  Backtest - Backbone 50, 5 years (~3 min)
echo  11.  Backtest - Full S&P 500, 5 years (~15 min)
echo  12.  Backtest - Test mode (10 stocks, 1 year, fast)
echo.
echo   --- Charts ---
echo  13.  Generate chart for single stock
echo  14.  Generate charts for top 5 picks from latest scan
echo.
echo   --- Validation ---
echo  15.  Verify picks (validate entry/SL/targets)
echo  16.  Sector rotation heatmap
echo  17.  Refresh S&P 500 stock list (from Wikipedia)
echo.
echo  18.  Exit
echo.
set /p choice="  Enter choice [1-18]: "

if "%choice%"=="1" goto SCAN_BACKBONE
if "%choice%"=="2" goto SCAN_SP500
if "%choice%"=="3" goto SCAN_SP500_ALL
if "%choice%"=="4" goto SCAN_TEST
if "%choice%"=="5" goto SCAN_CUSTOM
if "%choice%"=="6" goto SCAN_BEST
if "%choice%"=="7" goto SCAN_DB
if "%choice%"=="8" goto SCAN_BEST_DB
if "%choice%"=="9" goto BT_BACKBONE_3
if "%choice%"=="10" goto BT_BACKBONE_5
if "%choice%"=="11" goto BT_SP500_5
if "%choice%"=="12" goto BT_TEST
if "%choice%"=="13" goto CHART_SINGLE
if "%choice%"=="14" goto CHART_BATCH
if "%choice%"=="15" goto VERIFY
if "%choice%"=="16" goto SECTOR_HEAT
if "%choice%"=="17" goto REFRESH
if "%choice%"=="18" exit /b 0
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

:SCAN_BEST
cls
echo  === BEST SETUPS ONLY - 1 per stock, no duplicates (MTF) ===
echo  Eliminates duplicate entries (e.g., MSFT Monthly+Weekly+Daily = 1 pick)
echo  Uses backbone_us.txt. For S&P 500, add --stocks sp500.txt manually.
echo.
python scanner_us.py --top 30 --mtf-only --best-only
pause
goto MENU

:SCAN_DB
cls
echo  === DOUBLE BOTTOM ONLY - 70.7%% WR pattern (MTF) ===
echo  The highest-probability pattern from backtest (259 trades, +1.73%% exp).
echo  Most days will show 0 setups - that's normal. Wait for the right ones.
echo.
python scanner_us.py --top 30 --mtf-only --db-only
pause
goto MENU

:SCAN_BEST_DB
cls
echo  === BEST + DOUBLE BOTTOM - highest quality (MTF) ===
echo  Only Double Bottom setups, 1 per stock. The cream of the crop.
echo.
python scanner_us.py --top 30 --mtf-only --db-only --best-only
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
echo  Chart saved to charts_v3\ folder.
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

:REFRESH
cls
echo  === REFRESH S&P 500 STOCK LIST (from Wikipedia) ===
echo  Checks for new additions/delistings and updates sp500.txt.
echo.
echo  Step 1: Check what changed (dry run)...
python refresh_sp500.py --check
echo.
echo  Step 2: Apply changes? This updates sp500.txt + sp500_sectors.json.
set /p refconfirm="  Apply changes? [y/n]: "
if /i not "%refconfirm%"=="y" goto MENU
python refresh_sp500.py
echo.
echo  Step 3: Update cache (downloads only NEW stocks)?
set /p cacheconfirm="  Update backtest cache with new stocks? [y/n]: "
if /i not "%cacheconfirm%"=="y" goto MENU
python visual_backtest.py --stocks sp500.txt --years 5 --refresh-cache --visual
pause
goto MENU
