"""
Training pipeline for CryptoQuant models.

Primary model: Hybrid LSTM-CNN.
Secondary model: Gradient-boosted tabular baseline on the latest engineered row.
Served forecast: blended ensemble of neural, tree, and persistence.
"""
import logging
from datetime import datetime

import numpy as np

from shared.ml.evaluate import evaluate_model
from shared.ml.models import build_hybrid_model
from shared.ml.registry import get_model_registry
from shared.ml.tabular import assert_no_sequence_target_overlap, train_tabular_model
from shared.utils.data_fetcher import fetch_klines, fetch_market_context_data
from shared.utils.features import (
    add_market_context_indicators,
    add_sentiment_indicators,
    add_technical_indicators,
    get_feature_columns,
)
from shared.utils.preprocess import create_scaler

logger = logging.getLogger(__name__)

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]
FORECAST_HORIZON = 1
MIN_DIRECTIONAL_ACCURACY_TO_CACHE = 0.50

COIN_CONFIG = {
    "BTC": {"limit": 5000, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "ETH": {"limit": 5000, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "SOL": {"limit": 5000, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "BNB": {"limit": 5000, "lookback": 45, "dropout_rate": 0.35, "units": 64, "dense_units": 32},
    "ADA": {"limit": 5000, "lookback": 45, "dropout_rate": 0.35, "units": 64, "dense_units": 32},
}

ENSEMBLE_WEIGHTS = {"neural": 0.5, "tree": 0.3, "persistence": 0.2}


def _is_eligible_for_cached_serving(metrics: dict) -> bool:
    directional_accuracy = float(metrics.get("directional_accuracy", 0.0))
    mae = float(metrics.get("mae", np.inf))
    persistence_mae = float(metrics.get("persistence_mae", np.inf))

    if directional_accuracy < MIN_DIRECTIONAL_ACCURACY_TO_CACHE:
        return False
    if not (np.isfinite(mae) and np.isfinite(persistence_mae) and persistence_mae > 0):
        return False
    return mae <= persistence_mae * 3.0


def metrics_allow_cached_serving(metrics: dict | None) -> bool:
    return _is_eligible_for_cached_serving(metrics or {})


def _prepare_time_series_splits(
    df,
    coin: str,
    lookback: int,
    forecast_horizon: int,
    sentiment_df=None,
    market_context_df=None,
    target_col: str = "close",
):
    """
    Build chronological train/val/test splits without scaler leakage.
    """
    df = add_technical_indicators(df)
    df = add_sentiment_indicators(df, sentiment_df, coin=coin)
    df = add_market_context_indicators(df, market_context_df)

    feature_cols = get_feature_columns()
    df = df.dropna(subset=feature_cols)

    data = df[feature_cols].values
    target = df[[target_col]].values
    sample_ends = np.arange(lookback, len(data) - forecast_horizon + 1)

    if len(sample_ends) < 10:
        empty_X = np.empty((0, lookback, len(feature_cols)))
        empty_y = np.empty((0, forecast_horizon))
        return empty_X, empty_y, empty_X, empty_y, empty_X, empty_y, create_scaler(), create_scaler()

    train_end = int(len(sample_ends) * 0.7)
    val_end = int(len(sample_ends) * 0.8)
    gap = max(forecast_horizon, 1)

    feature_fit_end = sample_ends[train_end - 1]
    target_fit_end = sample_ends[train_end - 1] + forecast_horizon

    scaler = create_scaler()
    scaler.fit(data[:feature_fit_end])

    target_scaler = create_scaler()
    target_scaler.fit(target[:target_fit_end])

    scaled_data = scaler.transform(data)
    scaled_target = target_scaler.transform(target)

    X, y = [], []
    for end in sample_ends:
        assert_no_sequence_target_overlap(end, lookback, forecast_horizon)
        X.append(scaled_data[end - lookback:end])
        y.append(scaled_target[end:end + forecast_horizon, 0])

    X = np.array(X)
    y = np.array(y)

    return (
        X[:train_end],
        y[:train_end],
        X[train_end + gap:val_end],
        y[train_end + gap:val_end],
        X[val_end + gap:],
        y[val_end + gap:],
        scaler,
        target_scaler,
    )


def train_single_coin(coin_or_symbol: str, sentiment_df=None):
    symbol = coin_or_symbol if coin_or_symbol.endswith("USDT") else f"{coin_or_symbol}USDT"
    coin = symbol.replace("USDT", "")
    print(f"\n--- Training {symbol} ---")

    coin_cfg = COIN_CONFIG.get(
        coin,
        {"limit": 5000, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    )
    fetch_limit = coin_cfg["limit"]
    lookback = coin_cfg["lookback"]

    df = fetch_klines(symbol, limit=fetch_limit)
    if df is None or len(df) < 200:
        logger.error(f"Insufficient data for {symbol}: got {len(df) if df is not None else 0} rows")
        return None

    source = df["source"].iloc[0] if "source" in df.columns else "unknown"
    print(f"  Data source for {coin}: {source} ({len(df)} rows, lookback={lookback})")

    if source == "Mock":
        logger.error(f"Refusing to train {coin} on MOCK data. Please check network/API keys.")
        return None

    market_context_df = fetch_market_context_data(symbol, limit=fetch_limit)

    (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
        scaler,
        target_scaler,
    ) = _prepare_time_series_splits(
        df,
        coin=coin,
        lookback=lookback,
        forecast_horizon=FORECAST_HORIZON,
        sentiment_df=sentiment_df,
        market_context_df=market_context_df,
    )

    if len(X_train) < 50 or len(X_val) == 0 or len(X_test) == 0:
        total = len(X_train) + len(X_val) + len(X_test)
        logger.error(f"Too few samples for {symbol} after preprocessing: {total}")
        return None

    print(f"  Train samples: {len(X_train)}, Val samples: {len(X_val)}, Test samples: {len(X_test)}")

    input_shape = (X_train.shape[1], X_train.shape[2])
    neural_model = build_hybrid_model(
        input_shape,
        output_steps=FORECAST_HORIZON,
        dropout_rate=coin_cfg.get("dropout_rate", 0.3),
        lstm_units=coin_cfg.get("units", 128),
        dense_units=coin_cfg.get("dense_units", 64),
    )

    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=7,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    weights = np.exp(np.linspace(-1, 0, len(X_train)))

    print(f"  Fitting neural model on {len(X_train)} samples, validating on {len(X_val)} ...")
    batch_size = 32 if len(X_train) >= 320 else 16
    neural_model.fit(
        X_train,
        y_train,
        epochs=100,
        batch_size=batch_size,
        validation_data=(X_val, y_val),
        sample_weight=weights,
        callbacks=callbacks,
        verbose=1,
    )

    print("  Fitting tabular baseline ...")
    tree_model = train_tabular_model(X_train, y_train)

    raw_metrics = evaluate_model(neural_model, X_test, y_test, target_scaler, tabular_model=tree_model)
    metrics = {
        **raw_metrics,
        "trained_at": datetime.utcnow().isoformat(),
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "test_samples": int(len(X_test)),
        "eligible_for_cached_serving": _is_eligible_for_cached_serving(raw_metrics),
    }
    print(f"  Metrics for {coin}: {raw_metrics}")

    registry = get_model_registry()
    version = registry.save_model(
        coin,
        neural_model,
        scaler,
        target_scaler,
        metrics=metrics,
        tree_model=tree_model,
        config_overrides={
            "forecast_horizon": FORECAST_HORIZON,
            "ensemble_weights": ENSEMBLE_WEIGHTS,
            "feature_count": len(get_feature_columns()),
        },
    )
    print(f"  Registered {coin} as {version}")

    return version


def train_job_all_coins():
    from shared.utils.data_fetcher import fetch_sentiment_data

    print("Fetching sentiment data ...")
    sentiment_df = fetch_sentiment_data(limit=1000)

    results = {}
    for coin in COINS:
        try:
            version = train_single_coin(coin, sentiment_df=sentiment_df)
            results[coin] = version or "skipped (insufficient data)"
        except Exception as e:
            logger.exception(f"Training failed for {coin}")
            results[coin] = f"Error: {e}"

    return results
