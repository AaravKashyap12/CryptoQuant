"""
Training pipeline for CryptoQuant LSTM models.

train_single_coin   - Full pipeline for one coin: fetch, preprocess, train, evaluate, register.
train_job_all_coins - Sequential training for all supported coins.
"""
import logging
from datetime import datetime

import numpy as np

from shared.core.config import settings
from shared.ml.evaluate import evaluate_model
from shared.ml.models import build_hybrid_model
from shared.ml.registry import get_model_registry
from shared.utils.data_fetcher import fetch_klines
from shared.utils.features import add_sentiment_indicators, add_technical_indicators, get_feature_columns
from shared.utils.preprocess import create_scaler

logger = logging.getLogger(__name__)

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]

COIN_CONFIG = {
    "BTC": {"limit": 500, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "ETH": {"limit": 500, "lookback": 60, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "SOL": {"limit": 400, "lookback": 30, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
    "BNB": {"limit": 350, "lookback": 20, "dropout_rate": 0.4, "units": 64, "dense_units": 32},
    "ADA": {"limit": 350, "lookback": 20, "dropout_rate": 0.4, "units": 64, "dense_units": 32},
}


def _prepare_time_series_splits(
    df,
    coin: str,
    lookback: int,
    forecast_horizon: int,
    sentiment_df=None,
    target_col: str = "close",
):
    """
    Build chronological train/val/test sequence splits without scaler leakage.

    Scalers fit only on the training-era rows used by training sequences and
    labels. Validation and test rows are transformed with those fitted scalers.
    """
    df = add_technical_indicators(df)
    df = add_sentiment_indicators(df, sentiment_df, coin=coin)

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
        X.append(scaled_data[end - lookback:end])
        y.append(scaled_target[end:end + forecast_horizon, 0])

    X = np.array(X)
    y = np.array(y)

    return (
        X[:train_end],
        y[:train_end],
        X[train_end:val_end],
        y[train_end:val_end],
        X[val_end:],
        y[val_end:],
        scaler,
        target_scaler,
    )


def train_single_coin(coin_or_symbol: str, sentiment_df=None):
    """
    Full training pipeline for a single coin.

    Steps:
        1. Fetch OHLCV data using per-coin COIN_CONFIG.
        2. Engineer features, fit scalers on training rows only, and split 70/10/20.
        3. Build the hybrid LSTM-CNN model with per-coin capacity/dropout.
        4. Train with early stopping, validation-only model selection, and recency weights.
        5. Evaluate on untouched test sequences.
        6. Register model artifacts and metrics.
    """
    symbol = coin_or_symbol if coin_or_symbol.endswith("USDT") else f"{coin_or_symbol}USDT"
    coin = symbol.replace("USDT", "")
    print(f"\n--- Training {symbol} ---")

    coin_cfg = COIN_CONFIG.get(
        coin,
        {"limit": 500, "lookback": 30, "dropout_rate": 0.3, "units": 128, "dense_units": 64},
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
        forecast_horizon=7,
        sentiment_df=sentiment_df,
    )

    if len(X_train) < 50 or len(X_val) == 0 or len(X_test) == 0:
        total = len(X_train) + len(X_val) + len(X_test)
        logger.error(f"Too few samples for {symbol} after preprocessing: {total}")
        return None

    print(f"  Train samples: {len(X_train)}, Val samples: {len(X_val)}, Test samples: {len(X_test)}")

    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_hybrid_model(
        input_shape,
        output_steps=7,
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

    print(f"  Fitting on {len(X_train)} samples, validating on {len(X_val)} ...")
    model.fit(
        X_train,
        y_train,
        epochs=100,
        batch_size=16,
        validation_data=(X_val, y_val),
        sample_weight=weights,
        callbacks=callbacks,
        verbose=1,
    )

    raw_metrics = evaluate_model(model, X_test, y_test, target_scaler)
    metrics = {
        **raw_metrics,
        "trained_at": datetime.utcnow().isoformat(),
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "test_samples": int(len(X_test)),
    }
    print(f"  Metrics for {coin}: {raw_metrics}")

    registry = get_model_registry()
    version = registry.save_model(coin, model, scaler, target_scaler, metrics=metrics)
    print(f"  Registered {coin} as {version}")

    return version


def train_job_all_coins():
    """
    Train models for all supported coins sequentially.
    Fetches sentiment data once and reuses it across coins.
    """
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
