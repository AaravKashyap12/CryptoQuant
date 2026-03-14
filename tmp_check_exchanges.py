import os
import sys
import pandas as pd
sys.path.append(os.getcwd())
from shared.utils.data_fetcher import get_exchange_client

def check_exchanges():
    for ex_id in ['coinbase', 'kraken', 'kraken']:
        print(f"--- Checking {ex_id} ---")
        ex = get_exchange_client(ex_id)
        for pair in ['BTC/USDT', 'BTC/USD', 'XBT/USDT', 'XBT/USD']:
            try:
                o = ex.fetch_ohlcv(pair, '1d', limit=1000)
                df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                print(f" {pair}: Max={df['c'].max():.2f}, Last={df['c'].iloc[-1]:.2f}, Rows={len(df)}")
            except:
                continue

check_exchanges()
