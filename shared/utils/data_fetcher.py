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
_MARKET_CONTEXT_CACHE: dict = {}


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
def fetch_klines(symbol: str, interval: str = None, limit: int = 500, allow_mock: bool = None) -> pd.DataFrame:
    """
    Fetch historical klines with a two-tier cache:
      1. Redis (if USE_REDIS=true)  — survives restarts, shared across workers
      2. In-process dict             — fast local fallback / dev mode

    CCXT exchange priority: kraken → coinbase → binance → kucoin → okx
    Returns None when live exchanges fail. Mock data is only returned when
    allow_mock=True or ALLOW_MOCK_DATA=true, so production paths never silently
    serve synthetic prices.
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
        use_mock = settings.ALLOW_MOCK_DATA if allow_mock is None else allow_mock
        if not use_mock:
            print(f" [WARN] {symbol} fetch failed on all exchanges. Mock fallback disabled.")
            return None
        print(f" [WARN] {symbol} fetch failed on all exchanges. Falling back to MOCK data.")
        df = generate_mock_data(symbol, interval="1d", limit=limit)
        df["source"] = "Mock"

    # --- Populate caches ---
    expires_at = time.time() + ohlcv_ttl
    _LOCAL_OHLCV_CACHE[cache_key] = (expires_at, df)
    now = time.time()
    for key, (expiry, _) in list(_LOCAL_OHLCV_CACHE.items()):
        if now >= expiry:
            del _LOCAL_OHLCV_CACHE[key]

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


def fetch_market_context_data(symbol: str, limit: int = 500) -> pd.DataFrame:
    """
    Fetch public derivatives context for a symbol and return daily features.

    Uses Binance futures public endpoints for funding-rate history and open
    interest history. If either request fails, returns a neutral zero-filled
    dataframe so training and inference stay operational.
    """
    cache_key = f"context:{symbol}:{limit}"
    cached = _MARKET_CONTEXT_CACHE.get(cache_key)
    if cached is not None and time.time() < cached[0]:
        return cached[1]

    fallback_index = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="D")
    fallback = pd.DataFrame(
        {
            "funding_rate": np.zeros(limit),
            "open_interest": np.zeros(limit),
            "open_interest_change": np.zeros(limit),
        },
        index=fallback_index,
    )
    fallback.index.name = "open_time"

    try:
        funding_resp = requests.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": min(max(limit * 3, 30), 1000)},
            timeout=10,
        )
        oi_resp = requests.get(
            "https://fapi.binance.com/futures/data/openInterestHist",
            params={"symbol": symbol, "period": "1d", "limit": min(max(limit, 30), 500)},
            timeout=10,
        )
        funding_resp.raise_for_status()
        oi_resp.raise_for_status()

        funding_rows = funding_resp.json() or []
        oi_rows = oi_resp.json() or []
        if not funding_rows or not oi_rows:
            raise ValueError("empty market context payload")

        funding_df = pd.DataFrame(funding_rows)
        funding_df["open_time"] = pd.to_datetime(funding_df["fundingTime"], unit="ms").dt.floor("D")
        funding_df["funding_rate"] = pd.to_numeric(funding_df["fundingRate"], errors="coerce")
        funding_daily = funding_df.groupby("open_time", as_index=True)["funding_rate"].mean().to_frame()

        oi_df = pd.DataFrame(oi_rows)
        oi_df["open_time"] = pd.to_datetime(oi_df["timestamp"], unit="ms").dt.floor("D")
        oi_df["open_interest"] = pd.to_numeric(oi_df["sumOpenInterest"], errors="coerce")
        oi_daily = oi_df.groupby("open_time", as_index=True)["open_interest"].last().to_frame()
        oi_daily["open_interest_change"] = oi_daily["open_interest"].pct_change().replace([np.inf, -np.inf], np.nan)

        merged = funding_daily.join(oi_daily, how="outer").sort_index()
        merged = merged.reindex(fallback.index.union(merged.index)).sort_index()
        merged["funding_rate"] = merged["funding_rate"].fillna(0.0)
        merged["open_interest"] = merged["open_interest"].ffill().fillna(0.0)
        merged["open_interest_change"] = merged["open_interest_change"].fillna(0.0)
        merged = merged.tail(limit)
        merged.index.name = "open_time"
    except Exception as e:
        logger.warning(f"Market context fetch failed for {symbol}: {e}")
        merged = fallback

    _MARKET_CONTEXT_CACHE[cache_key] = (time.time() + 28_800, merged)
    return merged


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
    if rate:
        return rate
    return {"EUR": 0.92, "GBP": 0.79, "INR": 94.0, "AUD": 1.55, "JPY": 155.0, "CAD": 1.38}.get(
        target_currency, 1.0
    )
