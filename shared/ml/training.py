"""
Training pipeline for CryptoQuant LSTM models.

train_single_coin   — Full pipeline for one coin: fetch → preprocess → train → evaluate → register.
train_job_all_coins — Sequential training for all 5 supported coins.
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime

from shared.ml.models import build_hybrid_model
from shared.ml.registry import get_model_registry
from shared.utils.data_fetcher import fetch_klines
from shared.utils.preprocess import prepare_training_data
from shared.ml.evaluate import evaluate_model
from shared.core.config import settings

logger = logging.getLogger(__name__)

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]

# ── Per-coin fetch + model config ─────────────────────────────────────────────
# BNB and ADA receive fewer rows from fallback exchanges (~250-300 vs 700+ for
# BTC/ETH). A higher limit compensates for exchange caps. A shorter lookback
# means each training sequence needs fewer rows, giving 3-4x more training
# samples from the same dataset — critical for data-scarce coins.
#
# BTC/ETH have ample data so lookback=60 gives the model a fuller market cycle
# context (vs the previous lookback=30 for all coins).
COIN_CONFIG = {
    "BTC": {"limit": 1500, "lookback": 60},
    "ETH": {"limit": 1500, "lookback": 60},
    "SOL": {"limit": 1500, "lookback": 30},
    "BNB": {"limit": 2000, "lookback": 20},
    "ADA": {"limit": 1500, "lookback": 20},
}


def train_single_coin(coin_or_symbol: str, sentiment_df=None):
    """
    Full training pipeline for a single coin.

    Steps:
        1. Fetch OHLCV data (per-coin limit from COIN_CONFIG)
        2. Preprocess & scale features
        3. Build Hybrid LSTM-CNN model
        4. Train with early stopping (patience=8) + ReduceLROnPlateau
        5. Evaluate on hold-out test set
        6. Register in DB + upload artifacts to S3/Local

    Args:
        coin_or_symbol : e.g. "BTC" or "BTCUSDT"
        sentiment_df   : optional pre-fetched Fear & Greed DataFrame
                         (pass this in when training all coins to avoid repeated API calls)

    Returns:
        version string (e.g. "v1.0.3") or None on failure
    """
    symbol = coin_or_symbol if coin_or_symbol.endswith("USDT") else f"{coin_or_symbol}USDT"
    coin   = symbol.replace("USDT", "")
    print(f"\n--- Training {symbol} ---")

    # ── 1. Fetch ──────────────────────────────────────────────────────────────
    coin_cfg = COIN_CONFIG.get(coin, {"limit": 1500, "lookback": 30})
    fetch_limit = coin_cfg["limit"]
    lookback    = coin_cfg["lookback"]

    df = fetch_klines(symbol, limit=fetch_limit)
    if df is None or len(df) < 200:
        logger.error(f"Insufficient data for {symbol}: got {len(df) if df is not None else 0} rows")
        return None

    source = df["source"].iloc[0] if "source" in df.columns else "unknown"
    print(f"  Data source for {coin}: {source} ({len(df)} rows, lookback={lookback})")

    if source == "Mock":
        logger.error(f"Refusing to train {coin} on MOCK data. Please check network/API keys.")
        return None

    # ── 2. Preprocess ─────────────────────────────────────────────────────────
    X, y, scaler, target_scaler = prepare_training_data(
        df, lookback=lookback, forecast_horizon=7, sentiment_df=sentiment_df
    )

    if len(X) < 50:
        logger.error(f"Too few training samples for {symbol} after preprocessing: {len(X)}")
        return None

    # 80/20 chronological split (no shuffle — time series)
    split   = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    print(f"  Train samples: {len(X_train)}, Test samples: {len(X_test)}")

    # ── 3. Build ──────────────────────────────────────────────────────────────
    input_shape = (X_train.shape[1], X_train.shape[2])
    from shared.ml.models import build_model
    model = build_model(input_shape, output_steps=7, dropout_rate=0.2)

    # ── 4. Train ──────────────────────────────────────────────────────────────
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=15,
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

    print(f"  Fitting on {len(X_train)} samples, validating on {len(X_test)} …")
    model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=16,
        validation_data=(X_test, y_test),
        callbacks=callbacks,
        verbose=1,
    )

    # ── 5. Evaluate ───────────────────────────────────────────────────────────
    raw_metrics = evaluate_model(model, X_test, y_test, target_scaler)
    metrics = {
        **raw_metrics,
        "trained_at":    datetime.utcnow().isoformat(),
        "train_samples": int(len(X_train)),
        "test_samples":  int(len(X_test)),
    }
    print(f"  Metrics for {coin}: {raw_metrics}")

    # ── 6. Register ───────────────────────────────────────────────────────────
    registry = get_model_registry()
    version  = registry.save_model(coin, model, scaler, target_scaler, metrics=metrics)
    print(f"  Registered {coin} as {version}")

    return version


def train_job_all_coins():
    """
    Train models for all supported coins sequentially.
    Fetches sentiment data once and reuses it across coins.

    Returns:
        dict  coin → version_string or "Error: <message>"
    """
    from shared.utils.data_fetcher import fetch_sentiment_data

    print("Fetching sentiment data …")
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