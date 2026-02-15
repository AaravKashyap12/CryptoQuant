import pandas as pd
import numpy as np
from shared.ml.models import build_model
from shared.ml.registry import get_model_registry
from shared.utils.data_fetcher import fetch_klines
from shared.utils.preprocess import prepare_training_data
from shared.ml.evaluate import evaluate_model
from shared.core.config import settings
import logging

logger = logging.getLogger(__name__)

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]

def train_single_coin(coin_or_symbol: str):
    """
    Complete training pipeline for a single coin.
    1. Fetch Data
    2. Preprocess & Scale
    3. Build LSTM
    4. Train
    5. Evaluate
    6. Register in DB/S3
    """
    symbol = coin_or_symbol if coin_or_symbol.endswith("USDT") else f"{coin_or_symbol}USDT"
    coin = symbol.replace("USDT", "")
    
    print(f"--- Training Model for {symbol} ---")
    
    # 1. Fetch Data
    df = fetch_klines(symbol, limit=1000)
    if df is None or len(df) < 100:
        print(f"Error: Insufficient data for {symbol}")
        return None
        
    # 2. Preprocess
    # lookback 60, forecast 7 days
    X, y, scaler, target_scaler = prepare_training_data(df, lookback=60, forecast_horizon=7)
    
    # Split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # 3. Build Model
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_model(input_shape, output_steps=7)
    
    # 4. Train
    print(f"Fitting model (RAM usage might peak here)...")
    model.fit(
        X_train, y_train,
        epochs=10, # Short epochs for demo/base production
        batch_size=32,
        validation_data=(X_test, y_test),
        verbose=1
    )
    
    # 5. Evaluate
    metrics = evaluate_model(model, X_test, y_test, target_scaler)
    print(f"Final Metrics for {coin}: {metrics}")
    
    # 6. Save to Registry
    registry = get_model_registry()
    version = registry.save_model(coin, model, scaler, target_scaler, metrics=metrics)
    
    return version

def train_job_all_coins():
    """
    Train models for all supported coins in sequence.
    """
    results = {}
    for coin in COINS:
        try:
            version = train_single_coin(coin)
            results[coin] = version
        except Exception as e:
            print(f"Failed to train {coin}: {str(e)}")
            results[coin] = f"Error: {str(e)}"
            
    return results
