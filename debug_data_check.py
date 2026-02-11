
import sys
import os
import pandas as pd
import numpy as np

# Add backend directory to path to import backend modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from src.data_fetcher import fetch_klines

def debug_data_values(coin):
    """
    Inspect the raw data values to debug 1970 date issue.
    """
    symbol = f"{coin}USDT"
    print(f"Fetching data for {symbol}...")
    try:
        df = fetch_klines(symbol, limit=5)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    if df is None:
        print("Could not fetch data (None returned).")
        return
        
    print(f"Source: {df.iloc[-1].get('source', 'unknown') if 'source' in df.columns else 'unknown'}")
    print(f"Index Name: {df.index.name}")
    print(f"Index Dtype: {df.index.dtype}")
    print(f"Sample Index[0]: {df.index[0]}")
    print(f"Columns: {list(df.columns)}")
    
    # Test Conversion Logic
    df_test = df.copy()
    # Simulate what happens in endpoints.py: ensure index name is set
    df_test.index.name = "open_time"
    df_test.reset_index(inplace=True)
    
    print(f"Col Dtype Before: {df_test['open_time'].dtype}")
    print(f"Val Before[0]: {df_test['open_time'].iloc[0]}")
    
    # Perform conversion exactly as in market-data
    try:
        converted = df_test['open_time'].astype(np.int64) // 10**6
        val_after = int(converted.iloc[0])
        print(f"Val After[0] (int64 // 10^6): {val_after}")
        try:
             expected_year = pd.to_datetime(val_after, unit='ms').year
             print(f"Expected Year from Val After: {expected_year}")
        except Exception as e:
             print(f"Error converting back to datetime: {e}")

    except Exception as e:
        print(f"Conversion Error: {e}")

if __name__ == "__main__":
    debug_data_values("BTC")
