import os
import sys
sys.path.append(os.getcwd())
from shared.utils.data_fetcher import get_exchange_client
import pandas as pd

exchange = get_exchange_client('coinbase')
for pair in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
    try:
        ohlcv = exchange.fetch_ohlcv(pair, timeframe='1d', limit=5)
        print(f"{pair}: Last close {ohlcv[-1][4]}")
    except Exception as e:
        print(f"{pair} failed: {e}")
