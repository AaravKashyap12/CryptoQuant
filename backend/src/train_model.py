import os
import numpy as np
import tensorflow as tf
from src.data_fetcher import fetch_klines
from src.preprocess import prepare_training_data
from src.models import build_model
from src.registry import ModelRegistry

# Constants
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
LOOKBACK = 60
FORECAST_HORIZON = 7
EPOCHS = 15
BATCH_SIZE = 32

def train_single_coin(coin):
    """
    Train model for a single coin and return the new version.
    """
    print(f"\nStarting training for {coin}...")
    registry = ModelRegistry()
    
    # 1. Fetch Data
    df = fetch_klines(coin, limit=500) 
    if df is None:
        print(f"Skipping {coin} due to data fetch error.")
        return None
        
    print(f"Fetched {len(df)} rows.")
    
    # 2. Preprocess
    X, y, scaler, target_scaler = prepare_training_data(
        df, 
        lookback=LOOKBACK, 
        target_col='close', 
        forecast_horizon=FORECAST_HORIZON
    )
    
    if len(X) == 0:
        print("Not enough data to train.")
        return None
    
    # Split into Train/Validation
    split_idx = int(len(X) * 0.9)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_val, y_val = X[split_idx:], y[split_idx:]
    
    print(f"Training shapes: X={X_train.shape}, y={y_train.shape}")
    
    # 3. Build Model
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_model(
        input_shape=input_shape, 
        output_steps=FORECAST_HORIZON,
        dropout_rate=0.2
    )
    
    # 4. Train
    history = model.fit(
        X_train, y_train, 
        batch_size=BATCH_SIZE, 
        epochs=EPOCHS, 
        validation_data=(X_val, y_val),
        verbose=1
    )
    
    # 5. Save Model
    val_loss = min(history.history['val_loss'])
    mae = min(history.history['val_mae'])
    
    metrics = {
        "val_loss": float(val_loss),
        "val_mae": float(mae),
        "epochs": EPOCHS,
        "data_points": len(df)
    }
    
    version = registry.save_model(coin, model, scaler, target_scaler, metrics)
    print(f"Saved {coin} model version {version} to the registry (MAE: {mae:.4f})")
    
    return {
        "coin": coin,
        "version": version,
        "metrics": metrics
    }

def train_coins():
    """
    Train multi-step LSTM models for all defined coins.
    """
    for coin in COINS:
        train_single_coin(coin)

if __name__ == "__main__":
    train_coins()
