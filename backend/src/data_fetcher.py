import os
import pandas as pd
import numpy as np
from binance.client import Client
from dotenv import load_dotenv
import urllib3

# Load environment variables
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_binance_client():
    """
    Safely initialize Binance client. Returns None if connection fails.
    """
    try:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if api_key:
            api_key = api_key.strip().replace('\n', '').replace('\r', '')
        if api_secret:
            api_secret = api_secret.strip().replace('\n', '').replace('\r', '')
            
        client = Client(api_key, api_secret, requests_params={'verify': False})
        return client
    except Exception as e:
        print(f"Warning: Could not initialize Binance client: {e}")
        return None

def generate_mock_data(symbol, interval='1d', limit=500):
    """
    Generate realistic mock crypto data when API is blocked.
    """
    print(f"Generating mock data for {symbol} ({interval}) (API blocked)...")
    
    # Base price based on coin roughly (Updated to ~Feb 2026 levels)
    base_prices = {
        "BTCUSDT": 73500.0,
        "ETHUSDT": 4000.0,
        "BNBUSDT": 600.0,
        "SOLUSDT": 150.0,
        "ADAUSDT": 0.8
    }
    
    target_price = base_prices.get(symbol, 100.0)
    
    # Generate dates
    end_date = pd.Timestamp.now()
    
    # Set Frequency based on interval
    freq = 'D'
    if interval == '1h':
        freq = 'h'
        # For hourly, reduce volatility per step
        volatility = 0.005 
    elif interval == '15m':
        freq = '15min'
        volatility = 0.002
    else:
        # Daily
        volatility = 0.02

    dates = pd.date_range(end=end_date, periods=limit, freq=freq)
    
    # Random walk with Trend Bias
    returns = np.random.normal(0, volatility, limit)
    
    # Inject downtrend only for Daily data (simulation of macro trend)
    if freq == 'D':
        # Inject massive downtrend in the last 60 days
        returns[-60:] -= 0.005 

    # We build the price path backwards
    price_multipliers = np.exp(returns)
    
    prices = np.zeros(limit)
    prices[-1] = target_price
    
    for i in range(limit-2, -1, -1):
        prices[i] = prices[i+1] / price_multipliers[i+1] # Walk backwards
    
    # Create DataFrame
    df = pd.DataFrame(index=dates)
    df['open_time'] = dates
    df['close'] = prices
    
    # Synthetic OHLC
    start_price = prices[0]
    df['open'] = df['close'].shift(1).fillna(start_price)
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.rand(limit) * (volatility/2))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.rand(limit) * (volatility/2))
    df['volume'] = np.random.randint(1000, 100000, limit)
    
    return df[['close', 'open', 'high', 'low', 'volume']]

def fetch_klines(symbol, interval=None, limit=500): # interval default handled inside
    """
    Fetch historical klines (candlestick data) for a symbol.
    Uses Binance API if available. 
    If Direct Pair fails, falls back to BTCUSDT * ConversionRate.
    """
    client = get_binance_client()
    
    # Default interval if not passed
    binance_interval = interval
    mock_interval = '1d'

    if interval is None:
        binance_interval = Client.KLINE_INTERVAL_1DAY
    elif interval == Client.KLINE_INTERVAL_1HOUR:
        mock_interval = '1h'
    elif interval == Client.KLINE_INTERVAL_15MINUTE:
        mock_interval = '15m'

import yfinance as yf

def fetch_klines(symbol, interval=None, limit=500):
    """
    Fetch historical data using Yahoo Finance (No blocked regions).
    Symbol format: BTC-USD, ETH-USD
    """
    # Convert Binance symbol (BTCUSDT) to Yahoo symbol (BTC-USD)
    if symbol.endswith("USDT"):
        y_symbol = f"{symbol[:-4]}-USD"
    elif symbol.endswith("USD"):
        y_symbol = f"{symbol[:-3]}-USD"
    else:
        y_symbol = f"{symbol}-USD"

    try:
        # Map interval
        # yfinance supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        y_interval = "1d"
        if interval == Client.KLINE_INTERVAL_1HOUR:
            y_interval = "1h"
        elif interval == Client.KLINE_INTERVAL_15MINUTE:
            y_interval = "15m"

        # Fetch data
        # limit=500 -> ~2 years for daily
        period = "2y" 
        if y_interval == "1h":
            period = "1mo" # Hourly data is limited
        elif y_interval == "15m":
            period = "5d"

        print(f"Fetching {y_symbol} from Yahoo Finance ({y_interval})...")
        ticker = yf.Ticker(y_symbol)
        df = ticker.history(period=period, interval=y_interval)

        if df.empty:
            raise Exception("Empty dataframe from Yahoo")

        # Standardize columns
        df = df.reset_index()
        # Yahoo columns: Date, Open, High, Low, Close, Volume, Dividends, Stock Splits
        # Rename 'Date' or 'Datetime' to 'open_time'
        if 'Date' in df.columns:
            df.rename(columns={'Date': 'open_time'}, inplace=True)
        elif 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'open_time'}, inplace=True)

        # Ensure UTC and remove timezone for compatibility
        df['open_time'] = pd.to_datetime(df['open_time']).dt.tz_localize(None)

        df.set_index('open_time', inplace=True)
        df = df[['Close', 'Open', 'High', 'Low', 'Volume']]
        df.columns = ['close', 'open', 'high', 'low', 'volume'] # Lowercase
        
        df['source'] = 'Yahoo Finance'
        
        # Filter to limit
        if len(df) > limit:
            df = df.iloc[-limit:]

        return df

    except Exception as e:
        print(f"Yahoo Finance failed for {symbol}: {e}")
        # Fallback to Mock
        return generate_mock_data(symbol, interval='1d', limit=limit)

def get_current_price(symbol):
    """
    Fetch latest price from Yahoo Finance.
    """
    # Convert matches standard logic
    if symbol.endswith("USDT"):
        y_symbol = f"{symbol[:-4]}-USD"
    else:
        y_symbol = f"{symbol}-USD"

    try:
        ticker = yf.Ticker(y_symbol)
        # fast_info is often faster than history
        price = ticker.fast_info.last_price
        if price:
            return float(price)
            
        # Fallback to history
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
            
    except Exception as e:
        print(f"Yahoo Price check failed: {e}")
        
    return None

def get_live_rate(target_currency):
    """
    Fetch live forex rate from external API.
    """
    try:
        import requests
        # Free API (rate limit: ample for this use case)
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        rates = data.get('rates', {})
        return rates.get(target_currency)
    except Exception as e:
        print(f"Forex API failed: {e}")
        return None

def get_conversion_rate(target_currency):
    """
    Get conversion rate from USDT to target_currency.
    """
    if target_currency == 'USD':
        return 1.0
        
    # 1. Try Live Forex API (Most accurate for "Real" rates)
    live_rate = get_live_rate(target_currency)
    
    # Ad-hoc adjustment for INR (Crypto USDT premium in India is typically ~4-5% above Forex rate)
    # If user specifically compares to Binance INR display, they often use USDT P2P rates or similar.
    # We will add a small premium for INR to match "Crypto" expectations if it is INR.
    if live_rate and target_currency == 'INR':
        live_rate *= 1.04 # Approx 4% USDT premium
        
    if live_rate:
        return live_rate
        
    # 2. Fallback to Binance (Direct Pairs)
    client = get_binance_client()
    if client:
        try:
            ticker = client.get_symbol_ticker(symbol=f"{target_currency}USDT")
            return 1.0 / float(ticker['price'])
        except:
            pass
            
    # 3. Last Resort Fallbacks (Updated roughly for early 2026)
    fallbacks = {
        'EUR': 0.92,
        'GBP': 0.79,
        'INR': 94.0, # Updated fallback to reflect typical USDT P2P rates in India
        'AUD': 1.55,
        'JPY': 155.0,
        'CAD': 1.38
    }
    return fallbacks.get(target_currency, 1.0)

if __name__ == "__main__":
    df = fetch_klines("BTCUSDT", limit=5)
    print(df.head())
