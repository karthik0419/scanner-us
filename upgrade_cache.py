"""Add monthly resampled data to existing cache (in-place upgrade)."""
import pickle
import os
import sys

def upgrade_cache(cache_path):
    print(f"Loading cache: {cache_path}")
    with open(cache_path, 'rb') as f:
        data = pickle.load(f)

    print(f"  {len(data)} stocks in cache")

    # Check if already upgraded
    sample = next(iter(data.values()))
    if 'monthly' in sample:
        print("  Cache already has monthly data. Nothing to do.")
        return

    print("  Adding monthly resampled data to each stock...")
    for i, (symbol, stock_data) in enumerate(data.items(), 1):
        if 'daily' not in stock_data:
            continue
        df = stock_data['daily']
        if 'ATR' in df.columns:
            df_monthly = df.resample('ME').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            # Calculate ATR for monthly
            high_low = df_monthly['High'] - df_monthly['Low']
            high_close = (df_monthly['High'] - df_monthly['Close'].shift()).abs()
            low_close = (df_monthly['Low'] - df_monthly['Close'].shift()).abs()
            tr = high_low.combine(high_close, max).combine(low_close, max)
            df_monthly['ATR'] = tr.rolling(14).mean()
            stock_data['monthly'] = df_monthly

        if i % 100 == 0:
            print(f"    {i}/{len(data)}...")

    print(f"  Saving upgraded cache...")
    with open(cache_path, 'wb') as f:
        pickle.dump(data, f)
    print(f"  Done! Cache upgraded with monthly data.")

if __name__ == '__main__':
    cache_dir = os.path.join(os.path.dirname(__file__), 'backtest_cache')
    for fname in os.listdir(cache_dir):
        if fname.endswith('.pkl'):
            upgrade_cache(os.path.join(cache_dir, fname))
