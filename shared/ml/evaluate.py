import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from shared.ml.predict import (
    blend_predictions,
    persistence_forecast,
    predict_with_uncertainty,
    _persistence_envelope,
    _should_fallback_to_persistence,
)
from shared.ml.tabular import predict_tabular_model
from shared.utils.data_fetcher import fetch_market_context_data, fetch_sentiment_data
from shared.utils.features import (
    add_market_context_indicators,
    add_sentiment_indicators,
    add_technical_indicators,
    get_feature_columns,
)


def naive_baseline(data: np.ndarray, forecast_horizon: int) -> np.ndarray:
    return np.full(forecast_horizon, data[-1])


def _predict_batch_with_uncertainty(model, X: np.ndarray, n_iter: int = 50):
    mc_preds = []
    for _ in range(n_iter):
        mc_preds.append(model(X, training=True).numpy())
    preds = np.stack(mc_preds, axis=0)
    return np.mean(preds, axis=0), np.percentile(preds, 5, axis=0), np.percentile(preds, 95, axis=0)


def execute_rolling_backtest(
    coin: str,
    df: pd.DataFrame,
    days: int = 30,
    forecast_horizon: int = 1,
    n_iter: int = 10,
):
    from shared.ml.registry import get_model_registry

    registry = get_model_registry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)
    tree_model = registry.load_latest_aux_artifact(coin, "tree_model.pkl")

    if model is None:
        return None

    lookback = metadata["config"]["lookback"]
    horizon = int(metadata["config"].get("forecast_horizon", model.output_shape[1]))

    required_len = lookback + days + horizon
    if len(df) < required_len:
        return {"error": f"Not enough data. Need {required_len}, have {len(df)}"}

    df_proc = df.copy()
    df_proc.index.name = "open_time"

    df_full = add_technical_indicators(df_proc)
    df_full = add_sentiment_indicators(df_full, fetch_sentiment_data(limit=200), coin=coin)
    df_full = add_market_context_indicators(
        df_full,
        fetch_market_context_data(f"{coin}USDT", limit=max(len(df_full), 120)),
    )

    feature_cols = get_feature_columns()
    df_full = df_full.dropna(subset=feature_cols)

    if len(df_full) < (lookback + 1):
        return {"error": f"Not enough data after indicators. Need {lookback + 1}, have {len(df_full)}"}

    end_idx = len(df_full)
    start_idx = max(lookback, end_idx - days)
    raw_values = df_full[feature_cols].values
    expected_features = getattr(scaler, "n_features_in_", raw_values.shape[1])

    history = []
    for i in range(start_idx, end_idx - 1):
        input_start = i - lookback
        if input_start < 0:
            continue

        window = raw_values[input_start:i]
        if window.shape[1] < expected_features:
            return {
                "error": (
                    f"Feature count mismatch. Model expects {expected_features} features, "
                    f"but backtest generated {window.shape[1]}."
                )
            }
        if window.shape[1] > expected_features:
            window = window[:, :expected_features]
        scaled_window = scaler.transform(window)
        X_input = scaled_window.reshape(1, lookback, scaled_window.shape[1])

        neural_scaled, neural_lower_scaled, neural_upper_scaled = predict_with_uncertainty(model, X_input, n_iter=n_iter)
        tree_scaled = predict_tabular_model(tree_model, X_input)[0] if tree_model is not None else neural_scaled

        neural_price = target_scaler.inverse_transform(neural_scaled.reshape(-1, 1)).flatten()
        neural_lower = target_scaler.inverse_transform(neural_lower_scaled.reshape(-1, 1)).flatten()
        neural_upper = target_scaler.inverse_transform(neural_upper_scaled.reshape(-1, 1)).flatten()
        tree_price = target_scaler.inverse_transform(tree_scaled.reshape(-1, 1)).flatten()

        persistence_price = persistence_forecast(float(df_full.iloc[i - 1]["close"]), horizon)
        blended_mean, _, _ = blend_predictions(
            neural_mean=neural_price,
            neural_lower=neural_lower,
            neural_upper=neural_upper,
            tree_pred=tree_price,
            persistence_pred=persistence_price,
            weights=metadata.get("config", {}).get("ensemble_weights"),
        )

        last_close = float(df_full.iloc[i - 1]["close"])
        if _should_fallback_to_persistence(metadata, blended_mean, last_close, coin=coin):
            fallback_mean, _, _ = _persistence_envelope(df_full.iloc[:i], horizon)
            blended_mean = fallback_mean

        if i < len(df_full):
            history.append(
                {
                    "date": str(df_full.index[i]),
                    "actual": float(df_full.iloc[i]["close"]),
                    "predicted": float(blended_mean[0]),
                }
            )

    return history


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray, target_scaler, tabular_model=None) -> dict:
    from shared.ml.training import ENSEMBLE_WEIGHTS

    neural_scaled, neural_lower_scaled, neural_upper_scaled = _predict_batch_with_uncertainty(
        model,
        X_test,
        n_iter=50,
    )

    n_samples, horizon = neural_scaled.shape
    y_test_inv = target_scaler.inverse_transform(y_test.reshape(-1, 1)).reshape(n_samples, horizon)
    neural_inv = target_scaler.inverse_transform(neural_scaled.reshape(-1, 1)).reshape(n_samples, horizon)

    if tabular_model is not None:
        tree_scaled = predict_tabular_model(tabular_model, X_test)
        tree_inv = target_scaler.inverse_transform(tree_scaled.reshape(-1, 1)).reshape(n_samples, horizon)
    else:
        tree_inv = neural_inv

    neural_lower = target_scaler.inverse_transform(neural_lower_scaled.reshape(-1, 1)).reshape(n_samples, horizon)
    neural_upper = target_scaler.inverse_transform(neural_upper_scaled.reshape(-1, 1)).reshape(n_samples, horizon)
    last_close = target_scaler.inverse_transform(X_test[:, -1, 0].reshape(-1, 1)).flatten()
    persistence = np.vstack([persistence_forecast(close, horizon) for close in last_close])

    ensemble_mean = np.zeros_like(neural_inv)
    ensemble_lower = np.zeros_like(neural_inv)
    ensemble_upper = np.zeros_like(neural_inv)
    for idx in range(n_samples):
        blend_mean, blend_lower, blend_upper = blend_predictions(
            neural_mean=neural_inv[idx],
            neural_lower=neural_lower[idx],
            neural_upper=neural_upper[idx],
            tree_pred=tree_inv[idx],
            persistence_pred=persistence[idx],
            weights=ENSEMBLE_WEIGHTS,
        )
        ensemble_mean[idx] = blend_mean
        ensemble_lower[idx] = blend_lower
        ensemble_upper[idx] = blend_upper

    if n_samples > 1:
        actual_dir = np.sign(y_test_inv[:, 0] - last_close)
        pred_dir = np.sign(ensemble_mean[:, 0] - last_close)
        directional_accuracy = np.mean(pred_dir == actual_dir)
    else:
        directional_accuracy = 0.0

    return {
        "mae": float(mean_absolute_error(y_test_inv.flatten(), ensemble_mean.flatten())),
        "rmse": float(np.sqrt(mean_squared_error(y_test_inv.flatten(), ensemble_mean.flatten()))),
        "directional_accuracy": float(directional_accuracy),
        "neural_mae": float(mean_absolute_error(y_test_inv.flatten(), neural_inv.flatten())),
        "tree_mae": float(mean_absolute_error(y_test_inv.flatten(), tree_inv.flatten())),
        "persistence_mae": float(mean_absolute_error(y_test_inv.flatten(), persistence.flatten())),
        "horizon": int(horizon),
    }
