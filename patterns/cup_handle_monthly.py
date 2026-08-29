"""
G6 — Monthly-TF Cup & Handle.
Resamples daily → monthly and runs the full-tuned cup logic on it.
Useful for multi-year bases (DISHMAN, INDIGOPNTS, JSWENERGY long-term).
"""
from patterns.cup_handle import _detect


def resample_monthly(df_daily):
    return (df_daily.resample("ME")
                    .agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
                    .dropna())


def detect_cup_handle_monthly(df_monthly):
    result = _detect(
        df_monthly,
        cup_lengths    = [12, 18, 24, 36, 48, 60],   # 1y to 5y monthly cups
        handle_bars    = 3,                          # 3-month handle
        min_depth      = 0.20,
        max_depth      = 0.95,                       # very deep multi-year bases
        near_pct       = 0.05,                       # was 0.20 — NEAR means within 5% of breakout
        near_pct_watch = 0.10,                       # was 0.35 — WATCH means within 10%
        min_bars       = 18,
    )
    if result:
        result["pattern"]   = "Cup & Handle"
        result["timeframe"] = "Monthly"
    return result
