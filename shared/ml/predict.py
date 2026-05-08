import logging
import time

import numpy as np
import tensorflow as tf

from shared.ml.registry import get_model_registry
from shared.ml.tabular import predict_tabular_model
from shared.utils.features import get_feature_columns
from shared.utils.preprocess import prepare_inference_data

logger = logging.getLogger(__name__)

_compiled_fns: dict = {}


def _data_source_is_mock(df) -> bool:
    return "source" in df.columns and str(df["source"].iloc[0]).lower() == "mock"


def _get_compiled_fn(model):
    model_id = id(model)
    if model_id not in _compiled_fns:
        @tf.function(reduce_retracing=True)
        def _fn(x, training):
            return model(x, training=training)
        _compiled_fns[model_id] = _fn
    return _compiled_fns[model_id]


def predict_with_uncertainty(model, X: np.ndarray, n_iter: int = 50):
    X_batch = np.repeat(X, n_iter, axis=0)
    compiled_fn = _get_compiled_fn(model)
    predictions = compiled_fn(X_batch, training=(n_iter > 1)).numpy()

    return (
        np.mean(predictions, axis=0),
        np.percentile(predictions, 5, axis=0),
        np.percentile(predictions, 95, axis=0),
    )


def persistence_forecast(last_close: float, horizon: int) -> np.ndarray:
    return np.full(horizon, float(last_close))


def _persistence_envelope(df, horizon: int):
    last_close = float(df["close"].iloc[-1])
    mean = persistence_forecast(last_close, horizon)

    returns = df["close"].pct_change().dropna().tail(30)
    daily_vol = float(returns.std()) if len(returns) > 1 else 0.02
    if not np.isfinite(daily_vol) or daily_vol <= 0:
        daily_vol = 0.02

    z_score = 1.645  # approx 90% interval
    lower = []
    upper = []
    for step in range(1, horizon + 1):
        sigma = daily_vol * np.sqrt(step)
        lower.append(max(0.0, last_close * (1.0 - z_score * sigma)))
        upper.append(last_close * (1.0 + z_score * sigma))

    return mean, np.array(lower), np.array(upper)


def _max_one_day_move_for_coin(coin: str | None) -> float:
    # BTC/ETH should not serve huge one-day jumps from a weak/noisy model. Smaller
    # alts get more room because their daily volatility is naturally wider.
    limits = {"BTC": 0.08, "ETH": 0.10, "BNB": 0.15, "SOL": 0.18, "ADA": 0.18}
    return limits.get((coin or "").upper(), 0.15)


def _should_fallback_to_persistence(
    metadata: dict,
    blended_mean: np.ndarray,
    last_close: float,
    coin: str | None = None,
) -> bool:
    from shared.ml.training import FORECAST_HORIZON

    forecast_horizon = metadata.get("config", {}).get("forecast_horizon")
    feature_count = metadata.get("config", {}).get("feature_count")
    if feature_count is None:
        feature_count = metadata.get("config", {}).get("features")
    current_feature_count = len(get_feature_columns())

    try:
        forecast_horizon = int(forecast_horizon)
        feature_count = int(feature_count)
    except (TypeError, ValueError):
        return True

    legacy_artifact = (
        forecast_horizon is None
        or forecast_horizon != FORECAST_HORIZON
        or feature_count is None
        or feature_count != current_feature_count
    )
    if legacy_artifact:
        return True

    if not np.all(np.isfinite(blended_mean)):
        return True
    if np.any(blended_mean <= 0):
        return True
    max_move = _max_one_day_move_for_coin(coin) if FORECAST_HORIZON == 1 else 0.50
    if np.max(np.abs(blended_mean - last_close) / max(last_close, 1.0)) > max_move:
        return True
    return False


def _normalize_weights(weights: dict | None) -> dict:
    default = {"neural": 0.5, "tree": 0.3, "persistence": 0.2}
    weights = {**default, **(weights or {})}
    total = sum(max(float(weights.get(key, 0.0)), 0.0) for key in default)
    if total <= 0:
        return default
    return {key: max(float(weights.get(key, 0.0)), 0.0) / total for key in default}


def blend_predictions(
    neural_mean: np.ndarray,
    neural_lower: np.ndarray,
    neural_upper: np.ndarray,
    tree_pred: np.ndarray,
    persistence_pred: np.ndarray,
    weights: dict | None = None,
):
    weights = _normalize_weights(weights)
    # Neural is the primary learned signal; tree stabilizes tabular regimes;
    # persistence anchors the blend against noisy short-horizon overreaction.
    blended_mean = (
        weights["neural"] * neural_mean
        + weights["tree"] * tree_pred
        + weights["persistence"] * persistence_pred
    )

    component_stack = np.vstack([neural_mean, tree_pred, persistence_pred])
    model_spread = np.max(np.abs(component_stack - blended_mean), axis=0)
    neural_band = np.maximum(neural_mean - neural_lower, neural_upper - neural_mean)
    blended_spread = np.maximum(model_spread, neural_band * weights["neural"])
    blended_lower = np.maximum(0.0, blended_mean - blended_spread)
    blended_upper = blended_mean + blended_spread
    return blended_mean, blended_lower, blended_upper


def get_latest_prediction(coin: str, df, n_iter: int = 50):
    from shared.ml.training import FORECAST_HORIZON

    registry = get_model_registry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)

    if model is None:
        logger.warning(f"No model found for {coin}")
        return None

    lookback = metadata["config"]["lookback"]
    model_horizon = metadata["config"].get("forecast_horizon", model.output_shape[1])
    horizon = min(FORECAST_HORIZON, model_horizon)
    start_time = time.time()

    from shared.utils.data_fetcher import fetch_market_context_data, fetch_sentiment_data

    sentiment_df = fetch_sentiment_data(limit=500)
    market_context_df = fetch_market_context_data(f"{coin}USDT", limit=max(lookback * 4, 120))

    X_input = prepare_inference_data(
        df,
        scaler,
        lookback=lookback,
        sentiment_df=sentiment_df,
        market_context_df=market_context_df,
        coin=coin,
    )

    expected_lookback = model.input_shape[1]
    expected_features = model.input_shape[2]
    if X_input.shape[1] != expected_lookback or X_input.shape[2] != expected_features:
        raise ValueError(
            f"[{coin}] Input shape mismatch: model expects ({expected_lookback}, {expected_features}), "
            f"got ({X_input.shape[1]}, {X_input.shape[2]})."
        )

    mean_scaled, lower_scaled, upper_scaled = predict_with_uncertainty(model, X_input, n_iter=n_iter)
    mean_scaled = mean_scaled[:horizon]
    lower_scaled = lower_scaled[:horizon]
    upper_scaled = upper_scaled[:horizon]

    tree_model = registry.load_latest_aux_artifact(coin, "tree_model.pkl")
    if tree_model is not None:
        tree_scaled = predict_tabular_model(tree_model, X_input)[0][:horizon]
    else:
        tree_scaled = mean_scaled.copy()

    mean_price = target_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).flatten()
    lower_price = target_scaler.inverse_transform(lower_scaled.reshape(-1, 1)).flatten()
    upper_price = target_scaler.inverse_transform(upper_scaled.reshape(-1, 1)).flatten()
    tree_price = target_scaler.inverse_transform(tree_scaled.reshape(-1, 1)).flatten()

    last_close = float(df["close"].iloc[-1])
    persistence_price = persistence_forecast(last_close, horizon)

    blended_mean, blended_lower, blended_upper = blend_predictions(
        neural_mean=mean_price,
        neural_lower=lower_price,
        neural_upper=upper_price,
        tree_pred=tree_price,
        persistence_pred=persistence_price,
        weights=metadata.get("config", {}).get("ensemble_weights"),
    )

    degraded_to_persistence = _should_fallback_to_persistence(metadata, blended_mean, last_close, coin=coin)
    if degraded_to_persistence:
        blended_mean, blended_lower, blended_upper = _persistence_envelope(df, horizon)
        mean_price = blended_mean.copy()
        lower_price = blended_lower.copy()
        upper_price = blended_upper.copy()
        tree_price = blended_mean.copy()
        logger.warning(f"[Inference] {coin} falling back to persistence forecast for legacy or implausible model output")

    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"[Inference] {coin} latency={latency_ms:.1f}ms n_iter={n_iter}")

    from shared.ml.monitoring import log_prediction
    log_prediction(coin, metadata.get("version", "unknown"), X_input, mean_scaled, latency_ms)

    return {
        "mean": blended_mean,
        "lower": blended_lower,
        "upper": blended_upper,
        "metadata": {
            **metadata,
            "serving_mode": "weighted-neural-tree-persistence",
            "served_horizon": horizon,
            "mc_iterations": int(n_iter),
            "degraded_to_persistence": bool(degraded_to_persistence),
            "components": {
                "neural": mean_price.tolist(),
                "tree": tree_price.tolist(),
                "persistence": persistence_price.tolist(),
            },
        },
    }


def run_prediction_batch(coins=None, n_iter: int = 50):
    from shared.ml.training import COINS as ALL_COINS
    from shared.ml.training import COIN_CONFIG
    from shared.utils.data_fetcher import fetch_klines

    registry = get_model_registry()
    targets = coins or ALL_COINS
    results = {}

    for coin in targets:
        try:
            limit = COIN_CONFIG.get(coin, {}).get("limit", 500)
            df = fetch_klines(f"{coin}USDT", limit=limit)
            if df is None:
                results[coin] = "error: no data"
                continue
            if _data_source_is_mock(df):
                results[coin] = "skipped: mock data unavailable for cached serving"
                continue

            result = get_latest_prediction(coin, df, n_iter=n_iter)
            if result is None:
                results[coin] = "error: no model"
                continue
            metrics = (result["metadata"] or {}).get("metrics") or {}
            from shared.ml.training import metrics_allow_cached_serving

            if not metrics_allow_cached_serving(metrics):
                directional_accuracy = metrics.get("directional_accuracy")
                mae = metrics.get("mae")
                persistence_mae = metrics.get("persistence_mae")
                results[coin] = (
                    f"skipped: metrics below cache threshold "
                    f"(directional_accuracy={directional_accuracy}, mae={mae}, persistence_mae={persistence_mae})"
                )
                continue

            forecast = {
                "mean": result["mean"].tolist(),
                "lower": result["lower"].tolist(),
                "upper": result["upper"].tolist(),
            }
            registry.save_cached_prediction(coin, forecast, result["metadata"])
            results[coin] = "ok"
        except Exception as e:
            logger.exception(f"[Batch] {coin} failed: {e}")
            results[coin] = f"error: {e}"

    return results
