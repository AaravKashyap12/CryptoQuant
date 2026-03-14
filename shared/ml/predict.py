import numpy as np
import time
import logging
import tensorflow as tf
from shared.ml.registry import get_model_registry
from shared.utils.preprocess import prepare_inference_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# tf.function cache — compiled once per model object, reused on every call
# Reduces per-call CPU overhead by ~15-30% on TF CPU builds.
# ---------------------------------------------------------------------------
_compiled_fns: dict = {}

def _get_compiled_fn(model):
    model_id = id(model)
    if model_id not in _compiled_fns:
        @tf.function(reduce_retracing=True)
        def _fn(x, training):
            return model(x, training=training)
        _compiled_fns[model_id] = _fn
    return _compiled_fns[model_id]


# ---------------------------------------------------------------------------
# MC Dropout inference
# ---------------------------------------------------------------------------
def predict_with_uncertainty(model, X: np.ndarray, n_iter: int = 10):
    """
    Monte Carlo Dropout: runs n_iter forward passes in a single vectorised batch.

    Args:
        model  : Keras model with Dropout(training=True) layers
        X      : np.ndarray shape (1, lookback, n_features)
        n_iter : Stochastic passes. Use 1 for point-estimate, 5-10 for production.

    Returns:
        (mean, lower_5pct, upper_95pct) each shape (output_steps,)
    """
    X_batch = np.repeat(X, n_iter, axis=0)                   # (n_iter, lookback, features)
    compiled_fn = _get_compiled_fn(model)
    predictions = compiled_fn(X_batch, training=(n_iter > 1)).numpy()   # (n_iter, output_steps)

    return (
        np.mean(predictions, axis=0),
        np.percentile(predictions,  5, axis=0),
        np.percentile(predictions, 95, axis=0),
    )


# ---------------------------------------------------------------------------
# Main prediction entry point
# ---------------------------------------------------------------------------
def get_latest_prediction(coin: str, df, n_iter: int = 5):
    """
    Load the latest model for *coin*, prepare inference data from *df*,
    run MC Dropout, and return the result dict.

    n_iter=5 for user-facing requests (fast).
    n_iter=20 for scheduled batch jobs (higher quality).
    """
    registry = get_model_registry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)

    if model is None:
        logger.warning(f"No model found for {coin}")
        return None

    lookback = metadata["config"]["lookback"]
    start_time = time.time()

    # Sentiment is cached 8 h inside fetch_sentiment_data — safe to call here
    from shared.utils.data_fetcher import fetch_sentiment_data
    sentiment_df = fetch_sentiment_data(limit=500)

    X_input = prepare_inference_data(df, scaler, lookback=lookback, sentiment_df=sentiment_df)

    # FIX: Explicit shape guard before inference.
    # A mismatch between model's expected input and X_input produces silent wrong
    # predictions rather than an error. Catch it loudly here instead.
    expected_lookback  = model.input_shape[1]
    expected_features  = model.input_shape[2]
    if X_input.shape[1] != expected_lookback or X_input.shape[2] != expected_features:
        raise ValueError(
            f"[{coin}] Input shape mismatch: model expects ({expected_lookback}, {expected_features}), "
            f"got ({X_input.shape[1]}, {X_input.shape[2]}). "
            f"Retrain the model or verify feature columns are consistent."
        )

    mean_scaled, lower_scaled, upper_scaled = predict_with_uncertainty(model, X_input, n_iter=n_iter)

    mean_price  = target_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).flatten()
    lower_price = target_scaler.inverse_transform(lower_scaled.reshape(-1, 1)).flatten()
    upper_price = target_scaler.inverse_transform(upper_scaled.reshape(-1, 1)).flatten()

    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"[Inference] {coin} latency={latency_ms:.1f}ms n_iter={n_iter}")

    from shared.ml.monitoring import log_prediction
    log_prediction(coin, metadata.get("version", "unknown"), X_input, mean_scaled, latency_ms)

    return {
        "mean":     mean_price,
        "lower":    lower_price,
        "upper":    upper_price,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Scheduled batch — precompute and store predictions for all coins
# ---------------------------------------------------------------------------
def run_prediction_batch(coins=None, n_iter: int = 20):
    """
    Run inference for all coins and store results in the cached_predictions table.
    Called by the daily GitHub Actions job or POST /admin/predictions/refresh.
    """
    from shared.ml.training import COINS as ALL_COINS
    from shared.utils.data_fetcher import fetch_klines

    registry = get_model_registry()
    targets  = coins or ALL_COINS
    results  = {}

    for coin in targets:
        try:
            # FIX: Use configured limits per coin, not a generic 500 limit which was missing data for BNB/ADA
            from shared.ml.training import COIN_CONFIG
            limit = COIN_CONFIG.get(coin, {}).get("limit", 500) if "COIN_CONFIG" in locals() or "COIN_CONFIG" in globals() else 500
            
            df = fetch_klines(f"{coin}USDT", limit=limit)
            if df is None:
                results[coin] = "error: no data"
                continue

            result = get_latest_prediction(coin, df, n_iter=n_iter)
            if result is None:
                results[coin] = "error: no model"
                continue

            forecast = {
                "mean":  result["mean"].tolist(),
                "lower": result["lower"].tolist(),
                "upper": result["upper"].tolist(),
            }
            registry.save_cached_prediction(coin, forecast, result["metadata"])
            results[coin] = "ok"

        except Exception as e:
            logger.exception(f"[Batch] {coin} failed: {e}")
            results[coin] = f"error: {e}"

    return results