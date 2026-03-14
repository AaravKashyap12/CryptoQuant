import os
import pandas as pd
import numpy as np
import ccxt
import requests
import time
import logging
from datetime import datetime, timedelta

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process fallback cache (used when Redis is disabled)
# Survives within a process lifetime; evicted on restart.
# When USE_REDIS=true, the shared cache layer in shared/ml/cache.py is used.
# ---------------------------------------------------------------------------
_LOCAL_OHLCV_CACHE: dict = {}       # key → (expires_at, df)
_SENTIMENT_CACHE   = None
_SENTIMENT_EXPIRES = 0.0


def get_exchange_client(exchange_id: str):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        return exchange_class({"enableRateLimit": True, "timeout": 10000})
    except Exception as e:
        logger.debug(f"Failed to init {exchange_id}: {e}")
        return None


def generate_mock_data(symbol: str, interval: str = "1d", limit: int = 500) -> pd.DataFrame:
    """Realistic mock data used when all exchanges are unreachable (dev / CI)."""
    logger.warning(f"Generating mock data for {symbol} — all exchanges failed")

    base_prices = {
        "BTCUSDT": 73500.0, "ETHUSDT": 4000.0,
        "BNBUSDT": 600.0,   "SOLUSDT": 150.0, "ADAUSDT": 0.8,
    }
    target = base_prices.get(symbol, 100.0)

    freq       = "D" if interval == "1d" else ("h" if interval == "1h" else "15min")
    volatility = 0.02 if freq == "D" else (0.005 if freq == "h" else 0.002)

    dates   = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=freq)
    returns = np.random.normal(0, volatility, limit)
    if freq == "D":
        returns[-60:] -= 0.005

    price_multipliers = np.exp(returns)
    prices = np.zeros(limit)
    prices[-1] = target
    for i in range(limit - 2, -1, -1):
        prices[i] = prices[i + 1] / price_multipliers[i + 1]

    df = pd.DataFrame(index=dates)
    df["close"]  = prices
    df["open"]   = df["close"].shift(1).fillna(prices[0])
    df["high"]   = df[["open", "close"]].max(axis=1) * (1 + np.random.rand(limit) * volatility / 2)
    df["low"]    = df[["open", "close"]].min(axis=1) * (1 - np.random.rand(limit) * volatility / 2)
    df["volume"] = np.random.randint(1000, 100_000, limit).astype(float)
    return df[["close", "open", "high", "low", "volume"]]


# ---------------------------------------------------------------------------
# OHLCV fetch — with Redis-aware caching
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = None, limit: int = 500) -> pd.DataFrame:
    """
    Fetch historical klines with a two-tier cache:
      1. Redis (if USE_REDIS=true)  — survives restarts, shared across workers
      2. In-process dict             — fast local fallback / dev mode

    CCXT exchange priority: kraken → coinbase → binance → kucoin → okx
    Falls back to mock data if all fail.
    """
    from shared.core.config import settings

    if interval is None:
        interval = "1d"
        
    cache_key    = f"ohlcv:{symbol}:{interval}:{limit}"
    ohlcv_ttl    = settings.REDIS_OHLCV_TTL   # default 300s

    # --- Redis cache check ---
    if settings.USE_REDIS:
        from shared.ml.cache import cache
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"[OHLCV] Redis HIT {symbol}")
            idx = pd.DatetimeIndex(cached["index"])
            idx.name = "open_time"
            df_cached = pd.DataFrame(cached["data"], index=idx)
            if "source" in cached:
                df_cached["source"] = cached["source"]
            return df_cached

    # --- In-process cache check ---
    local = _LOCAL_OHLCV_CACHE.get(cache_key)
    if local and time.time() < local[0]:
        logger.debug(f"[OHLCV] Local HIT {symbol}")
        return local[1]

    # --- Live fetch ---
    base         = symbol.replace("USDT", "")
    target_pairs = [f"{base}/USDT", f"{base}/USD"]
    # Promote kraken and coinbase for better reliability on Render (Binance often blocks Render/AWS IPs)
    # Per-symbol exchange priority overrides.
    # BNB: KuCoin has 1500 rows (2022-present) vs Coinbase's 143 rows (2025-present)
    # without this, the fallback chain hits Coinbase first and starves BNB of training data.
    EXCHANGE_PRIORITY = {
        "BNBUSDT": ["kucoin", "binance", "kraken", "okx"],
        "ADAUSDT": ["kucoin", "kraken", "binance", "okx"],
    }
    exchange_ids = EXCHANGE_PRIORITY.get(symbol, ["kraken", "coinbase", "kucoin", "okx", "binance"])
    timeframe    = "1d"
    if interval == "1h":  timeframe = "1h"
    elif interval == "15m": timeframe = "15m"

    df = None
    for ex_id in exchange_ids:
        exchange = get_exchange_client(ex_id)
        if not exchange:
            continue
        for pair in target_pairs:
            try:
                ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
                if not ohlcv or len(ohlcv) < 10:
                    continue
                df = pd.DataFrame(ohlcv, columns=["open_time", "open", "high", "low", "close", "volume"])
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col])
                # Align with feature_cols order: close, high, low, open, volume
                df = df[["close", "high", "low", "open", "volume"]]
                df["source"] = f"CCXT ({ex_id})"
                break
            except Exception:
                continue
        if df is not None:
            break

    if df is None:
        print(f" [WARN] {symbol} fetch failed on all exchanges. Falling back to MOCK data.")
        df = generate_mock_data(symbol, interval="1d", limit=limit)
        df["source"] = "Mock"

    # --- Populate caches ---
    expires_at = time.time() + ohlcv_ttl
    _LOCAL_OHLCV_CACHE[cache_key] = (expires_at, df)

    if settings.USE_REDIS:
        from shared.ml.cache import cache
        data_cols = [c for c in df.columns if c != "source"]
        
        # Determine source (handle possible variations safely)
        source_val = df["source"].iloc[0] if "source" in df.columns and len(df) > 0 else "unknown"
        
        serialisable = {
            "index": [str(i) for i in df.index],
            "data":  df[data_cols].reset_index(drop=True).to_dict(orient="list"),
            "source": source_val
        }
        cache.set(cache_key, serialisable, ttl=ohlcv_ttl)

    return df


# ---------------------------------------------------------------------------
# Sentiment fetch
# ---------------------------------------------------------------------------
def fetch_sentiment_data(limit: int = 100) -> pd.DataFrame | None:
    """
    Fetch Fear & Greed index from alternative.me.
    Cached for 8 hours (in-process only — small payload, no need for Redis).
    """
    global _SENTIMENT_CACHE, _SENTIMENT_EXPIRES

    if _SENTIMENT_CACHE is not None and time.time() < _SENTIMENT_EXPIRES:
        return _SENTIMENT_CACHE

    try:
        url      = f"https://api.alternative.me/fng/?limit={limit}"
        response = requests.get(url, timeout=10)
        data     = response.json()

        if data.get("metadata", {}).get("error"):
            # Instead of returning empty cache, return a neutral fallback
            df = pd.DataFrame({
                "open_time": pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="D"),
                "value": [50.0] * limit
            }).set_index("open_time")
            return df

        df = pd.DataFrame(data.get("data", []))
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["value"]     = pd.to_numeric(df["value"])
        df = df[["timestamp", "value"]].rename(
            columns={"value": "sentiment_score", "timestamp": "open_time"}
        )
        df.set_index("open_time", inplace=True)

        _SENTIMENT_CACHE   = df.sort_index()
        _SENTIMENT_EXPIRES = time.time() + 28_800   # 8 hours
        return _SENTIMENT_CACHE

    except Exception as e:
        logger.warning(f"Sentiment fetch failed: {e}")
        # Return neutral fallback on exception
        df = pd.DataFrame({
            "open_time": pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="D"),
            "value": [50.0] * limit
        }).set_index("open_time")
        return df


# ---------------------------------------------------------------------------
# Live price / forex helpers (unchanged)
# ---------------------------------------------------------------------------
def get_current_price(symbol: str) -> float | None:
    base = symbol.replace("USDT", "")
    for ex_id in ["kraken", "coinbase", "binance", "kucoin"]:
        exchange = get_exchange_client(ex_id)
        if not exchange:
            continue
        for pair in [f"{base}/USDT", f"{base}/USD"]:
            try:
                ticker = exchange.fetch_ticker(pair)
                if ticker.get("last"):
                    return float(ticker["last"])
            except Exception:
                continue
    return None


def get_live_rate(target_currency: str) -> float | None:
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        return r.json().get("rates", {}).get(target_currency)
    except Exception as e:
        logger.debug(f"Forex API failed: {e}")
        return None


def get_conversion_rate(target_currency: str) -> float:
    if target_currency == "USD":
        return 1.0
    rate = get_live_rate(target_currency)
    if rate and target_currency == "INR":
        rate *= 1.04
    if rate:
        return rate
    return {"EUR": 0.92, "GBP": 0.79, "INR": 94.0, "AUD": 1.55, "JPY": 155.0, "CAD": 1.38}.get(
        target_currency, 1.0
    )
