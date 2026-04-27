import logging
import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]


def _coin_fetch_limit(coin: str, default: int = 500) -> int:
    from shared.ml.training import COIN_CONFIG
    return COIN_CONFIG.get(coin, {}).get("limit", default)


# ---------------------------------------------------------------------------
# Helper: verify admin API key for protected endpoints
# ---------------------------------------------------------------------------
def _require_admin(x_api_key: Optional[str] = Header(None)):
    from shared.core.config import settings
    if settings.ADMIN_API_KEY and x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


# ===========================================================================
# PUBLIC ENDPOINTS
# ===========================================================================

@router.get("/coins", response_model=List[str])
def get_supported_coins():
    return COINS


@router.get("/sentiment")
def get_sentiment():
    from shared.utils.data_fetcher import fetch_sentiment_data

    df = fetch_sentiment_data(limit=1)
    if df is None or df.empty:
        return {"sentiment_score": 50.0}

    return {"sentiment_score": float(df["sentiment_score"].iloc[-1])}


# ---------------------------------------------------------------------------
# Market data — cached via Redis or in-process (5-min TTL)
# ---------------------------------------------------------------------------
@router.get("/market-data/{coin}")
def get_market_data(coin: str, limit: int = 100):
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
    try:
        from shared.utils.data_fetcher import fetch_klines
        df = fetch_klines(f"{coin}USDT", limit=limit)
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch market data")

        if df.index.name != "open_time":
            df.index.name = "open_time"
        
        # Only reset index if open_time is actually the index and NOT yet a column
        if "open_time" not in df.columns:
            df = df.reset_index()

        if "open_time" in df.columns:
            df["open_time"] = pd.to_datetime(df["open_time"])
            # Safer conversion to milliseconds
            df["open_time"] = (df["open_time"].astype('int64') // 10**6)

        # Clean non-JSON compliant values (NaN, Inf) which often cause 500 errors in FastAPI serialization
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        return df.to_dict(orient="records")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"Market Data Error for {coin}: {error_msg}")
        raise HTTPException(
            status_code=500, 
            detail=f"Market Data Error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Predict — serves from cached_predictions table; falls back to live inference
# ---------------------------------------------------------------------------
@router.post("/predict/{coin}")
def predict_coin(coin: str):
    """
    Returns a 7-day forecast.

    Fast path (< 100ms): reads from the cached_predictions DB table, then
    checks Redis. The table is populated by the daily training pipeline or
    by POST /admin/predictions/refresh.

    Slow path (fallback): runs live inference if no fresh result exists.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")

    # ── 1. Check Redis ──────────────────────────────────────────────────────
    from shared.core.config import settings
    from shared.ml.cache import cache

    redis_key = f"pred:{coin}"
    cached    = cache.get(redis_key)
    if cached:
        logger.info(f"[/predict/{coin}] Redis HIT")
        cached["from_cache"] = True
        return cached

    # ── 2. Check DB prediction store ───────────────────────────────────────
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    db_cached = registry.get_cached_prediction(coin)
    if db_cached:
        logger.info(f"[/predict/{coin}] DB cache HIT")
        # Warm Redis for the next request
        cache.set(redis_key, db_cached, ttl=settings.REDIS_PREDICTION_TTL)
        return {
            "coin": coin,
            "forecast": db_cached["forecast"],
            "metadata": db_cached["metadata"],
            "computed_at": db_cached.get("computed_at"),
            "from_cache": True,
        }

    # ── 3. Live inference fallback ─────────────────────────────────────────
    logger.info(f"[/predict/{coin}] Cache MISS — running live inference")
    try:
        from shared.utils.data_fetcher import fetch_klines
        from shared.ml.predict import get_latest_prediction

        df = fetch_klines(f"{coin}USDT", limit=_coin_fetch_limit(coin))
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch data for prediction")

        result = get_latest_prediction(coin, df, n_iter=10)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No model found for {coin}")

        forecast = {
            "mean":  result["mean"].tolist(),
            "lower": result["lower"].tolist(),
            "upper": result["upper"].tolist(),
        }
        response = {
            "coin":     coin,
            "forecast": forecast,
            "metadata": result["metadata"],
            "from_cache": False,
        }

        # Store in DB + Redis so subsequent requests are fast
        registry.save_cached_prediction(coin, forecast, result["metadata"])
        cache.set(redis_key, response, ttl=settings.REDIS_PREDICTION_TTL)

        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction Error: {e}")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@router.get("/metrics/{coin}")
def get_model_metrics(coin: str):
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    _, _, _, metadata = registry.load_latest_model(coin)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"No model metadata for {coin}")
    return metadata


# ---------------------------------------------------------------------------
# Validate — LAZY: only runs when explicitly requested, not on page load
# ---------------------------------------------------------------------------
@router.get("/validate/{coin}")
def validate_model_endpoint(coin: str, days: int = 30):
    """
    Rolling backtest for the last N days. This is an expensive operation —
    call it on-demand (e.g. user opens the Accuracy panel), not on page load.
    Results are cached for 24 hours.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")

    from shared.core.config import settings
    from shared.ml.cache import cache

    cache_key = f"validate:{coin}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"[/validate/{coin}] cache HIT")
        return cached

    from shared.utils.data_fetcher import fetch_klines
    from shared.ml.evaluate import execute_rolling_backtest

    df = fetch_klines(f"{coin}USDT", limit=max(_coin_fetch_limit(coin), 200 + days))
    if df is None:
        raise HTTPException(status_code=500, detail="Failed to fetch data")

    history = execute_rolling_backtest(coin, df, days=days)
    if history is None:
        return []

    cache.set(cache_key, history, ttl=settings.REDIS_VALIDATION_TTL)
    return history


# ===========================================================================
# ADMIN ENDPOINTS (protected by X-API-Key header)
# ===========================================================================

@router.post("/admin/predictions/refresh")
def refresh_all_predictions(background_tasks: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    """
    Trigger a full prediction batch for all 5 coins.
    Runs in a background thread so the response is immediate.
    Call this from the daily GitHub Actions workflow instead of the old /train endpoint.
    """
    _require_admin(x_api_key)

    def _run():
        from shared.ml.predict import run_prediction_batch
        results = run_prediction_batch(n_iter=20)
        logger.info(f"[Admin] Batch prediction results: {results}")
        # Invalidate Redis prediction cache so next user request gets fresh data
        from shared.ml.cache import cache
        for coin in COINS:
            cache.delete(f"pred:{coin}")

    background_tasks.add_task(_run)
    return {"status": "batch_started", "coins": COINS}


@router.post("/admin/predictions/refresh/{coin}")
def refresh_prediction(coin: str, x_api_key: Optional[str] = Header(None)):
    """Refresh prediction for a single coin synchronously."""
    _require_admin(x_api_key)
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")

    from shared.utils.data_fetcher import fetch_klines
    from shared.ml.predict import get_latest_prediction
    from shared.ml.registry import get_model_registry
    from shared.ml.cache import cache

    df = fetch_klines(f"{coin}USDT", limit=_coin_fetch_limit(coin))
    if df is None:
        raise HTTPException(status_code=500, detail="Data fetch failed")

    result = get_latest_prediction(coin, df, n_iter=20)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No model for {coin}")

    forecast = {
        "mean":  result["mean"].tolist(),
        "lower": result["lower"].tolist(),
        "upper": result["upper"].tolist(),
    }
    registry = get_model_registry()
    registry.save_cached_prediction(coin, forecast, result["metadata"])
    cache.delete(f"pred:{coin}")   # invalidate so next request re-reads from DB

    return {"status": "ok", "coin": coin, "version": result["metadata"].get("version")}


@router.post("/admin/cache/flush")
def flush_cache(x_api_key: Optional[str] = Header(None)):
    """Flush all Redis / in-process caches."""
    _require_admin(x_api_key)
    from shared.ml.cache import cache
    n = cache.flush_pattern("")
    return {"status": "flushed", "keys_deleted": n}


# ===========================================================================
# DEBUG ENDPOINTS (disable in production by setting DEBUG=false)
# ===========================================================================

@router.get("/debug/system")
def system_diagnostics():
    from shared.core.config import settings
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Debug disabled in production")

    report = {"status": "ok", "steps": {}}
    import sys, platform
    report["steps"]["system"] = {"python": sys.version, "platform": platform.platform()}

    try:
        import tensorflow as tf
        report["steps"]["tensorflow"] = {
            "status": "ok",
            "version": tf.__version__,
            "gpu_available": len(tf.config.list_physical_devices("GPU")) > 0,
        }
    except Exception as e:
        report["steps"]["tensorflow"] = {"status": "failed", "error": str(e)}
        report["status"] = "degraded"

    try:
        from shared.utils.data_fetcher import fetch_klines
        df = fetch_klines("BTCUSDT", limit=10)
        report["steps"]["data_fetcher"] = {
            "status": "ok",
            "rows":   len(df) if df is not None else 0,
        }
    except Exception as e:
        report["steps"]["data_fetcher"] = {"status": "failed", "error": str(e)}

    try:
        from shared.ml.registry import get_model_registry
        registry = get_model_registry()
        v = registry.get_latest_version("BTC")
        report["steps"]["model_registry"] = {"latest_btc_version": v}
    except Exception as e:
        report["steps"]["model_registry"] = {"status": "failed", "error": str(e)}

    try:
        from shared.ml.cache import cache
        cache.set("_health_check", 1, ttl=10)
        ok = cache.get("_health_check") == 1
        report["steps"]["cache"] = {"status": "ok" if ok else "warn"}
    except Exception as e:
        report["steps"]["cache"] = {"status": "failed", "error": str(e)}

    return report


@router.get("/debug/data/{coin}")
def debug_data_values(coin: str):
    from shared.core.config import settings
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Debug disabled in production")

    from shared.utils.data_fetcher import fetch_klines
    df = fetch_klines(f"{coin}USDT", limit=5)
    if df is None:
        return {"error": "Could not fetch data"}

    df_test = df.copy()
    df_test.index.name = "open_time"
    df_test.reset_index(inplace=True)

    info = {
        "index_dtype": str(df.index.dtype),
        "sample_index": str(df.index[0]),
        "columns": list(df.columns),
    }
    try:
        converted = df_test["open_time"].astype(np.int64) // 10 ** 6
        info["val_after_0"]    = int(converted.iloc[0])
        info["expected_year"]  = pd.to_datetime(converted.iloc[0], unit="ms").year
    except Exception as e:
        info["conversion_error"] = str(e)
    return info


# ---------------------------------------------------------------------------
# TFJS model file serving
# ---------------------------------------------------------------------------
@router.get("/model/{coin}/tfjs/{filename}")
def get_tfjs_model_file(coin: str, filename: str):
    from shared.ml.registry import get_model_registry
    from shared.core.config import settings
    import os, tempfile

    registry = get_model_registry()
    meta = registry.get_latest_version_metadata(coin)
    if not meta:
        raise HTTPException(status_code=404, detail="Model not found")

    s3_prefix = meta["s3_key_prefix"]

    if settings.USE_S3:
        tmp_dir    = tempfile.gettempdir()
        local_path = os.path.join(tmp_dir, filename)
        try:
            registry.storage.load_file(f"{s3_prefix}/tfjs/{filename}", local_path)
            return FileResponse(local_path)
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
    else:
        local_path = os.path.join(settings.LOCAL_STORAGE_DIR, s3_prefix, "tfjs", filename)
        if os.path.exists(local_path):
            return FileResponse(local_path)
        raise HTTPException(status_code=404, detail="File not found")
