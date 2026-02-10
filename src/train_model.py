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
EPOCHS = 50
BATCH_SIZE = 32

def train_coins():
    """
    Train multi-step LSTM models for all defined coins and save them to the registry.
    """
    registry = ModelRegistry()
    
    for coin in COINS:
        print(f"\nStarting training for {coin}...")
        
        # 1. Fetch Data
        # Fetch more data for better training (limit=2000 ~ 5.5 years)
        df = fetch_klines(coin, limit=2000) 
        if df is None:
            print(f"Skipping {coin} due to data fetch error.")
            continue
            
        print(f"Fetched {len(df)} rows.")
        
        # 2. Preprocess (Multivariate + Multi-step)
        # Returns inputs X, targets y, and both scalers
        X, y, scaler, target_scaler = prepare_training_data(
            df, 
            lookback=LOOKBACK, 
            target_col='close', 
            forecast_horizon=FORECAST_HORIZON
        )
        
        # Split into Train/Validation
        split_idx = int(len(X) * 0.9)
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_val, y_val = X[split_idx:], y[split_idx:]
        
        print(f"Training shapes: X={X_train.shape}, y={y_train.shape}")
        
        # 3. Build Model
        # Input shape: (LOOKBACK, n_features)
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
        
        # 5. Save Model via Registry
        # Verify performance (min val_loss)
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

if __name__ == "__main__":
    train_coins()
