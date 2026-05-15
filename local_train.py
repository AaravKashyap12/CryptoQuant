"""
Standalone local trainer for the frontend-only CryptoQuant app.

It fetches daily Binance candles, trains a small TF/Keras model per coin,
and exports TF.js artifacts to:

    frontend/public/models/BTC/model.json

Run:
    python local_train.py
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tensorflow as tf

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]
FEATURE_COUNT = 15
LOOKBACK = 60
LIMIT = 1000
EPOCHS = int(os.getenv("CQ_EPOCHS", "30"))
OUTPUT_ROOT = Path("frontend/public/models")


def fetch_klines(symbol: str, limit: int = LIMIT) -> list[dict]:
    query = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": "1d",
        "limit": limit,
    })
    url = f"https://api.binance.com/api/v3/klines?{query}"
    with urllib.request.urlopen(url, timeout=30) as response:
        rows = json.loads(response.read().decode("utf-8"))

    candles = []
    for row in rows:
        candles.append({
            "open_time": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        })
    return candles


def ema(values: np.ndarray, period: int) -> np.ndarray:
    result = np.zeros_like(values, dtype=np.float32)
    result[0] = values[0]
    alpha = 2 / (period + 1)
    for i in range(1, len(values)):
        result[i] = values[i] * alpha + result[i - 1] * (1 - alpha)
    return result


def rolling_mean(values: np.ndarray, period: int) -> np.ndarray:
    result = np.zeros_like(values, dtype=np.float32)
    for i in range(len(values)):
        start = max(0, i - period + 1)
        result[i] = float(np.mean(values[start:i + 1]))
    return result


def rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    result = np.full(len(closes), 50.0, dtype=np.float32)
    if len(closes) <= period:
        return result

    deltas = np.diff(closes)
    gains = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    result[period] = 100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)

    for i in range(period + 1, len(closes)):
        avg_gain = avg_gain * (1 - 1 / period) + float(gains[i - 1]) * (1 / period)
        avg_loss = avg_loss * (1 - 1 / period) + float(losses[i - 1]) * (1 / period)
        result[i] = 100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return result


def feature_rows(candles: list[dict], sentiment_score: float = 50) -> np.ndarray:
    closes = np.array([c["close"] for c in candles], dtype=np.float32)
    highs = np.array([c["high"] for c in candles], dtype=np.float32)
    lows = np.array([c["low"] for c in candles], dtype=np.float32)
    opens = np.array([c["open"] for c in candles], dtype=np.float32)
    volumes = np.array([c["volume"] for c in candles], dtype=np.float32)

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    ema7 = ema(closes, 7)
    ema25 = ema(closes, 25)
    ema50 = ema(closes, 50)
    macd_line = ema12 - ema26
    macd_signal = ema(macd_line, 9)
    macd_hist = macd_line - macd_signal

    prev_close = np.concatenate(([closes[0]], closes[:-1]))
    true_range = np.maximum.reduce([
        highs - lows,
        np.abs(highs - prev_close),
        np.abs(lows - prev_close),
    ])

    rows = np.column_stack([
        closes,
        highs,
        lows,
        opens,
        volumes,
        rsi(closes),
        macd_line,
        macd_hist,
        macd_signal,
        ema7,
        ema25,
        ema50,
        rolling_mean(true_range, 14),
        rolling_mean(volumes, 20),
        np.full(len(candles), sentiment_score, dtype=np.float32),
    ]).astype(np.float32)

    if rows.shape[1] != FEATURE_COUNT:
        raise ValueError(f"Expected {FEATURE_COUNT} features, got {rows.shape[1]}")
    return rows


def build_samples(candles: list[dict], lookback: int = LOOKBACK) -> tuple[np.ndarray, np.ndarray]:
    rows = feature_rows(candles)
    closes = np.array([c["close"] for c in candles], dtype=np.float32)

    X, y = [], []
    for end in range(lookback + 50, len(rows) - 1):
        X.append(rows[end - lookback:end])
        y.append(closes[end])

    if not X:
        raise ValueError("Not enough candles to build training windows")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_model(lookback: int, feature_count: int, X_train: np.ndarray) -> tf.keras.Model:
    normalizer = tf.keras.layers.Normalization(axis=-1, name="feature_normalizer")
    normalizer.adapt(X_train.reshape(-1, feature_count))

    inputs = tf.keras.Input(shape=(lookback, feature_count), name="features")
    x = normalizer(inputs)
    x = tf.keras.layers.LSTM(64, return_sequences=True)(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.LSTM(32)(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1, name="next_close")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model


def export_tfjs(model: tf.keras.Model, output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import tensorflowjs as tfjs

        tfjs.converters.save_keras_model(model, str(output_dir))
        return True
    except Exception as exc:
        fallback = output_dir / "model.keras"
        model.save(fallback)
        print(f"  [WARN] TF.js export failed: {exc}")
        print(f"  Saved Keras fallback at {fallback}")
        print("  Install tensorflowjs to export model.json: pip install tensorflowjs")
        return False


def train_coin(coin: str) -> dict:
    symbol = f"{coin}USDT"
    print(f"\n=== {symbol} ===")
    candles = fetch_klines(symbol)
    print(f"Fetched {len(candles)} daily candles")

    X, y = build_samples(candles)
    split = math.floor(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    model = build_model(LOOKBACK, FEATURE_COUNT, X_train)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=3, factor=0.5, min_lr=1e-5),
    ]
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=32,
        callbacks=callbacks,
        verbose=1,
    )

    val_loss, val_mae = model.evaluate(X_val, y_val, verbose=0)
    output_dir = OUTPUT_ROOT / coin
    exported = export_tfjs(model, output_dir)

    metadata = {
        "coin": coin,
        "symbol": symbol,
        "lookback": LOOKBACK,
        "feature_count": FEATURE_COUNT,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "samples": int(len(X)),
        "validation_mae": float(val_mae),
        "validation_loss": float(val_loss),
        "tfjs_exported": exported,
        "epochs_ran": len(history.history.get("loss", [])),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Exported {coin} to {output_dir} (MAE {val_mae:,.2f})")
    return metadata


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    print("CryptoQuant frontend-only local trainer")
    print(f"Output: {OUTPUT_ROOT.resolve()}")
    print(f"Epochs: {EPOCHS}")

    results = {}
    for coin in COINS:
        try:
            results[coin] = train_coin(coin)
            time.sleep(0.5)
        except Exception as exc:
            results[coin] = {"error": str(exc)}
            print(f"[FAIL] {coin}: {exc}")

    summary_path = OUTPUT_ROOT / "training-summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSummary written to {summary_path}")

    failed = [coin for coin, result in results.items() if "error" in result]
    if failed:
        raise SystemExit(f"Training failed for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
