import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
from shared.utils.data_fetcher import fetch_sentiment_data
from shared.utils.features import add_sentiment_indicators, get_feature_columns, add_technical_indicators


def naive_baseline(data: np.ndarray, forecast_horizon: int) -> np.ndarray:
    """Predicts the last observed value for all future steps (persistence baseline)."""
    return np.full(forecast_horizon, data[-1])


def execute_rolling_backtest(coin: str, df: pd.DataFrame, days: int = 30, forecast_horizon: int = 7):
    """
    Performs a rolling backtest over the last *days* candles.
    Returns list of {date, actual, predicted} dicts, or None / error dict on failure.

    FIX: Previously scaler.transform() was called on the FULL dataframe before
         slicing the backtest window. The scaler was fitted during training on
         historical data — applying it to the full df (which includes rows the
         training scaler never saw) introduces subtle distribution leakage into
         the normalised values, making backtest metrics look better than reality.

         Fix: use the saved training scaler as-is (don't re-fit, don't
         transform future rows eagerly). Slice first, then transform only the
         window needed for each prediction. This matches real inference behaviour.
    """
    from shared.ml.registry import get_model_registry

    registry = get_model_registry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)

    if model is None:
        return None

    lookback = metadata["config"]["lookback"]

    required_len = lookback + days + forecast_horizon
    if len(df) < required_len:
        return {"error": f"Not enough data. Need {required_len}, have {len(df)}"}

    # ── Process ──────────────────────────────────────────────────────────
    df_proc = df.copy()
    df_proc.index.name = "open_time"

    source = df_proc["source"].iloc[0] if "source" in df_proc.columns else "unknown"
    print(f"[Backtest] {coin} source={source} rows={len(df_proc)}")

    df_full = add_technical_indicators(df_proc)

    sentiment_df = fetch_sentiment_data(limit=200)
    df_full = add_sentiment_indicators(df_full, sentiment_df, coin=coin)

    feature_cols = get_feature_columns()

    # FIX: Drop NaN after ALL indicators and sentiment are added (not before),
    # so the dropna sees the complete feature set and doesn't misalign columns.
    df_full = df_full.dropna(subset=feature_cols)

    if len(df_full) < (lookback + 1):
        return {"error": f"Not enough data after indicators. Need {lookback + 1}, have {len(df_full)}"}

    # ── Build batch ───────────────────────────────────────────────────────
    # FIX: Scale only the rows each prediction window actually uses.
    # Do NOT transform the full df upfront — the training scaler was fitted
    # on historical data only; applying it wholesale to a df that includes
    # the target rows leaks future distribution into normalised inputs.
    end_idx   = len(df_full)
    start_idx = max(lookback, end_idx - days)

    batch_X       = []
    valid_indices = []

    raw_values = df_full[feature_cols].values

    for i in range(start_idx, end_idx):
        input_start = i - lookback
        if input_start >= 0:
            # Transform only this window — matches real inference behaviour
            window = raw_values[input_start:i]
            scaled_window = scaler.transform(window)
            batch_X.append(scaled_window)
            valid_indices.append(i)

    if not batch_X:
        return []

    batch_X = np.array(batch_X)   # (N, lookback, features)

    print(f"[Backtest] {coin}: running {len(batch_X)}-day MC Dropout inference (n_iter=5) …")

    # MC Dropout inference: run 5 stochastic forward passes and average.
    # This matches production inference behaviour and produces smoother,
    # more accurate predictions than a single deterministic pass.
    n_iter = 5
    mc_preds = []
    for _ in range(n_iter):
        preds = model(batch_X, training=True).numpy()
        mc_preds.append(preds)
    all_preds_scaled = np.mean(mc_preds, axis=0)

    # Take t+1 step of each prediction, inverse-transform
    first_step = all_preds_scaled[:, 0].reshape(-1, 1)
    all_preds  = target_scaler.inverse_transform(first_step).flatten()

    history = []
    for idx, i in enumerate(valid_indices):
        # We predict i+1, so the actual needs to be at i+1
        # Check if i+1 exists
        if i + 1 < len(df_full):
            history.append({
                "date":      str(df_full.index[i + 1]),
                "actual":    float(df_full.iloc[i + 1]["close"]),
                "predicted": float(all_preds[idx]),
            })

    return history


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray, target_scaler) -> dict:
    """
    Evaluate model on held-out test set. Returns MAE, RMSE, and horizon.

    Note: y_test shape is (samples, forecast_horizon). inverse_transform
    expects (samples, 1) or (samples, n_features). We flatten across the
    horizon dimension so each step is evaluated independently then averaged.
    """
    # Evaluate with MC Dropout passes to match inference behaviour (5 passes)
    n_iter = 5
    mc_preds = []
    for _ in range(n_iter):
        preds = model(X_test, training=True).numpy()
        mc_preds.append(preds)
    
    y_pred_scaled = np.mean(mc_preds, axis=0)

    # Inverse transform step by step across horizon to avoid shape issues
    n_samples, horizon = y_pred_scaled.shape

    y_pred_inv = target_scaler.inverse_transform(
        y_pred_scaled.reshape(-1, 1)
    ).reshape(n_samples, horizon)

    y_test_inv = target_scaler.inverse_transform(
        y_test.reshape(-1, 1)
    ).reshape(n_samples, horizon)

    if n_samples > 1:
        actual_dir = np.sign(y_test_inv[1:, 0] - y_test_inv[:-1, 0])
        pred_dir = np.sign(y_pred_inv[1:, 0] - y_test_inv[:-1, 0])
        directional_accuracy = np.mean(pred_dir == actual_dir)
    else:
        directional_accuracy = 0.0

    return {
        "mae":     float(mean_absolute_error(y_test_inv.flatten(), y_pred_inv.flatten())),
        "rmse":    float(np.sqrt(mean_squared_error(y_test_inv.flatten(), y_pred_inv.flatten()))),
        "directional_accuracy": float(directional_accuracy),
        "horizon": int(horizon),
    }
