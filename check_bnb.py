import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()
from shared.utils.data_fetcher import fetch_klines

df = fetch_klines('BNBUSDT', limit=2000)
print(f'Rows: {len(df)}')
print(f'Source: {df["source"].iloc[0]}')
print(f'Date range: {df.index[0]} to {df.index[-1]}')
print(f'Last close: {df["close"].iloc[-1]}')
