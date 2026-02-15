import os
import sys
import numpy as np
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WorkerTask")

from shared.utils.data_fetcher import fetch_klines
from shared.utils.preprocess import prepare_training_data
from shared.ml.models import build_model
from shared.ml.registry import ModelRegistry

# Constants
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
LOOKBACK = 60
FORECAST_HORIZON = 7
EPOCHS = 15
BATCH_SIZE = 32

def train_job_all_coins():
    """
    Main job function called by scheduler.
    """
    logger.info("Starting scheduled training job...")
    results = []
    
    for coin in COINS:
        try:
            res = train_single_coin(coin)
            if res:
                results.append(res)
        except Exception as e:
            logger.error(f"Failed to train {coin}: {e}")
            import traceback
            traceback.print_exc()

    logger.info(f"Job complete. Trained {len(results)}/{len(COINS)} models.")

def train_single_coin(coin):
    """
    Train model for a single coin and return the new version.
    """
    logger.info(f"Training {coin}...")
    registry = ModelRegistry()
    
    # 1. Fetch Data
    # Fetch enough data for training + lookback
    df = fetch_klines(coin, limit=1000) 
    if df is None or len(df) < (LOOKBACK + FORECAST_HORIZON + 100):
        logger.warning(f"Skipping {coin}: Insufficient data ({len(df) if df is not None else 0} rows)")
        return None
        
    # 2. Preprocess
    X, y, scaler, target_scaler = prepare_training_data(
        df, 
        lookback=LOOKBACK, 
        target_col='close', 
        forecast_horizon=FORECAST_HORIZON
    )
    
    if len(X) == 0:
        logger.warning(f"Skipping {coin}: Zero samples after preprocessing")
        return None
    
    # Split into Train/Validation
    split_idx = int(len(X) * 0.9)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_val, y_val = X[split_idx:], y[split_idx:]
    
    # 3. Build Model
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_model(
        input_shape=input_shape, 
        output_steps=FORECAST_HORIZON,
        dropout_rate=0.2
    )
    
    # 4. Train
    model.fit(
        X_train, y_train, 
        batch_size=BATCH_SIZE, 
        epochs=EPOCHS, 
        validation_data=(X_val, y_val),
        verbose=0 # Silent training for worker logs
    )
    
    # 5. Evaluate (on validation set)
    # Just grab history metrics or evaluate?
    # history object has 'val_loss'
    eval_result = model.evaluate(X_val, y_val, verbose=0)
    
    # model.evaluate can return float or list
    if isinstance(eval_result, list):
        val_loss = eval_result[0]
    else:
        val_loss = eval_result
    
    metrics = {
        "val_loss": float(val_loss),
        "epochs": EPOCHS,
        "data_points": len(df)
    }
    
    # 6. Save Model
    version = registry.save_model(coin, model, scaler, target_scaler, metrics)
    logger.info(f"SUCCESS: {coin} -> {version} (Loss: {val_loss:.4f})")
    
    return {
        "coin": coin,
        "version": version,
        "metrics": metrics
    }
