import os
import pandas as pd
import numpy as np
import ccxt
import requests
import time
from datetime import datetime, timedelta

# Disable SSL warnings if needed (though usually fine with requests)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_exchange_client(exchange_id):
    """
    Initialize a specific CCXT exchange client.
    """
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 10000,
        })
        return exchange
    except Exception as e:
        print(f"Failed to initialize {exchange_id}: {e}")
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

def fetch_klines(symbol, interval=None, limit=500):
    """
    Fetch historical klines using CCXT (Multi-Exchange Fallback).
    Prioritizes Kraken -> Coinbase -> Binance (Public) -> KuCoin.
    """
    # Map Symbol to Standard CCXT Format
    # Input: BTCUSDT
    # Standard: BTC/USDT or BTC/USD
    
    base = symbol.replace("USDT", "")
    target_pairs = [f"{base}/USDT", f"{base}/USD"]
    
    # Exchanges to try in order
    # Kraken/Coinbase are very reliable for public data without keys
    exchange_ids = ['kraken', 'coinbase', 'binance', 'kucoin', 'okx']
    
    timeframe = '1d'
    # Map standard intervals
    if interval == '1h':
        timeframe = '1h'
    elif interval == '15m':
        timeframe = '15m'
        
    for ex_id in exchange_ids:
        exchange = get_exchange_client(ex_id)
        if not exchange:
            continue
            
        for pair in target_pairs:
            try:
                # Check if exchange supports the pair (optional, prevents 404s but fetch_ohlcv handles it)
                # Just try fetch directly
                
                # print(f"Fetching {pair} from {ex_id}...")
                ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
                
                if not ohlcv or len(ohlcv) < 10:
                    continue
                    
                # CCXT structure: [timestamp, open, high, low, close, volume]
                df = pd.DataFrame(ohlcv, columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert timestamp (ms) to datetime
                df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
                df.set_index('open_time', inplace=True)
                
                # Convert numeric
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
                
                # Filter just in case
                df = df[['close', 'open', 'high', 'low', 'volume']]
                df['source'] = f"CCXT ({ex_id})"
                
                # Handle USD conversion if needed?
                # Usually close enough to USDT to ignore for this app.
                # If pair is BTC/USD and we want USDT, it's 1:1 effectively.
                
                return df
                
            except Exception as e:
                # print(f"Failed to fetch {pair} from {ex_id}: {e}")
                continue
                
    # Fallback to Mock
    print(f"All CCXT exchanges failed for {symbol}. Using Mock Data.")
    df = generate_mock_data(symbol, interval='1d', limit=limit)
    df['source'] = 'Mock'
    return df

def get_current_price(symbol):
    """
    Fetch current price using CCXT.
    """
    base = symbol.replace("USDT", "")
    target_pairs = [f"{base}/USDT", f"{base}/USD"]
    
    exchange_ids = ['kraken', 'coinbase', 'binance', 'kucoin']
    
    for ex_id in exchange_ids:
        exchange = get_exchange_client(ex_id)
        if not exchange:
            continue
            
        for pair in target_pairs:
            try:
                ticker = exchange.fetch_ticker(pair)
                price = ticker['last']
                if price:
                    return float(price)
            except:
                continue
                
    return None

def get_live_rate(target_currency):
    """
    Fetch live forex rate from external API.
    """
    try:
        # Free API
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
    Get conversion rate from USDT (USD) to target_currency.
    """
    if target_currency == 'USD':
        return 1.0
        
    # 1. Try Live Forex API
    live_rate = get_live_rate(target_currency)
    
    if live_rate and target_currency == 'INR':
        live_rate *= 1.04 # USDT Premium
        
    if live_rate:
        return live_rate
        
    # 2. Hardcoded Fallbacks
    fallbacks = {
        'EUR': 0.92,
        'GBP': 0.79,
        'INR': 94.0,
        'AUD': 1.55,
        'JPY': 155.0,
        'CAD': 1.38
    }
    return fallbacks.get(target_currency, 1.0)

if __name__ == "__main__":
    df = fetch_klines("BTCUSDT", limit=5)
    print(df.head())
    print(f"Source: {df.iloc[-1].get('source')}")
