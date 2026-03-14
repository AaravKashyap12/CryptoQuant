import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()
from shared.utils.data_fetcher import get_exchange_client
import pandas as pd

exchanges = ['kraken', 'kucoin', 'okx', 'binance']
pairs = ['BNB/USDT', 'BNB/USD']

for ex_id in exchanges:
    ex = get_exchange_client(ex_id)
    if not ex:
        print(f'{ex_id}: failed to init')
        continue
    for pair in pairs:
        try:
            ohlcv = ex.fetch_ohlcv(pair, timeframe='1d', limit=2000)
            if ohlcv and len(ohlcv) > 10:
                df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
                print(f'{ex_id} {pair}: {len(df)} rows | last={df["c"].iloc[-1]:.2f} | from={pd.to_datetime(df["t"].iloc[0], unit="ms").date()}')
                break
        except Exception as e:
            print(f'{ex_id} {pair}: {e}')