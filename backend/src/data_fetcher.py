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

    if client:
        try:
            # 1. Try Direct Pair (e.g. BTCEUR)
            klines = client.get_klines(symbol=symbol, interval=binance_interval, limit=limit)
            
            cols = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ]
            
            df = pd.DataFrame(klines, columns=cols)
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
            
            df.set_index('open_time', inplace=True)
            df = df[['close', 'open', 'high', 'low', 'volume']]
            df['source'] = 'Binance Direct'
            return df
            
        except Exception as e:
            # 2. Fallback: Try Base+USDT and convert
            # Only if error suggests invalid symbol and it's not already USDT
            if "Invalid symbol" in str(e) and not symbol.endswith("USDT"):
                # Guess Base and Quote
                # Most quotes are 3 chars (EUR, INR, GBP). USDT is 4.
                # If we are here, it's likely a 3-char quote like 'INR'.
                quote = symbol[-3:] 
                base = symbol[:-3]
                
                start_symbol = f"{base}USDT"
                try:
                    # Fetch USDT Pair (Recursively to handle mocking if needed, but usually we want real data)
                    # We call client.get_klines directly to avoid infinite recursion quirks or ambiguity
                    klines = client.get_klines(symbol=start_symbol, interval=binance_interval, limit=limit)
                    
                    cols = [
                        'open_time', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ]
                    df = pd.DataFrame(klines, columns=cols)
                    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
                    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
                    df.set_index('open_time', inplace=True)
                    df = df[['close', 'open', 'high', 'low', 'volume']]
                    
                    # Convert to Target Currency
                    rate = get_conversion_rate(quote)
                    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']] * rate
                    # Volume is in Base Asset (BTC), so it stays same? 
                    # Binance "volume" is usually Base Asset Volume. "quote_asset_volume" is Quote.
                    # We keep volume as is (Base Asset amount).
                    
                    df['source'] = f'Binance Converted ({start_symbol} -> {quote})'
                    return df
                    
                except Exception as e2:
                    print(f"Fallback to {start_symbol} failed: {e2}")
            else:
                 print(f"Binance API error for {symbol}: {e}")

            # Fall through to mock data
            
    # Final Fallback: Mock
    df = generate_mock_data(symbol, interval=mock_interval, limit=limit)
    df['source'] = 'Mock'
    return df

def get_current_price(symbol):
    """
    Fetch the absolute latest price for a symbol.
    Prioritizes direct pair, but handles missing pairs gracefully by converting from USDT.
    """
    client = get_binance_client()
    if client:
        try:
            # 1. Try Direct
            ticker = client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            # 2. Fallback
            if "Invalid symbol" in str(e) and not symbol.endswith("USDT"):
                quote = symbol[-3:]
                base = symbol[:-3]
                try:
                    ticker = client.get_symbol_ticker(symbol=f"{base}USDT")
                    usdt_price = float(ticker['price'])
                    rate = get_conversion_rate(quote)
                    return usdt_price * rate
                except:
                    pass
            # print(f"Error fetching current price for {symbol}: {e}")
            pass
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
