import os
import sys
sys.path.append(os.getcwd())
from shared.utils.data_fetcher import fetch_klines

for coin in ['BTC', 'ETH', 'SOL']:
    df = fetch_klines(f"{coin}USDT", limit=1000)
    if df is not None:
        print(f"{coin}: {len(df)} rows from {df['source'].iloc[0]}")
        print(f"   Range: {df.index[0]} to {df.index[-1]}")
        print(f"   Last Price: {df['close'].iloc[-1]}")
    else:
        print(f"{coin}: No data")
