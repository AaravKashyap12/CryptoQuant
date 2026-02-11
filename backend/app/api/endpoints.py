from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
import pandas as pd
from src.data_fetcher import fetch_klines
from src.predict import get_latest_prediction
from src.registry import ModelRegistry

router = APIRouter()

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]
print("ENDPOINTS MODULE LOADED -------------------------------------")
# FORCE_SYNTAX_ERROR

@router.get("/coins", response_model=List[str])
def get_supported_coins():
    """List of supported coins."""
    return COINS

@router.get("/market-data/{coin}")
def get_market_data(coin: str, limit: int = 100):
    """
    Get historical OHLCV data for a coin.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    symbol = f"{coin}USDT"
    df = fetch_klines(symbol, limit=limit)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Failed to fetch data from Binance")
        
    # Convert to JSON-compatible format
    df.reset_index(inplace=True) # Make timestamp a column
    return df.to_dict(orient="records")

@router.post("/predict/{coin}")
def predict_coin(coin: str):
    """
    Generate 7-day price forecast with confidence intervals.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")

    symbol = f"{coin}USDT"
        
    try:
        # Fetch recent data for inference
        df = fetch_klines(symbol, limit=500)
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch data needed for prediction")
        
        # Log data shape for debugging
        print(f"DEBUG: Fetched {len(df)} rows for {symbol} from {df.iloc[-1].get('source', 'Unknown')}")
        
        result = get_latest_prediction(symbol, df)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Model not found or prediction failed")
            
        return {
            "coin": coin,
            "forecast": {
                "mean": result['mean'].tolist(),
                "lower": result['lower'].tolist(),
                "upper": result['upper'].tolist()
            },
            "metadata": result['metadata']
        }
    except Exception as e:
        import traceback
        traceback.print_exc() # Print to server logs
        print(f"CRITICAL ERROR in /predict: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")

@router.get("/metrics/{coin}")
def get_model_metrics(coin: str):
    """
    Get the latest model health metrics from the registry.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    symbol = f"{coin}USDT"
    registry = ModelRegistry()
    _, _, _, metadata = registry.load_latest_model(symbol)
    
    if metadata is None:
        raise HTTPException(status_code=404, detail="No model metadata found")
        
    return metadata
@router.get("/validate/{coin}")
def validate_model(coin: str, days: int = 30):
    """
    Run a rolling backtest to compare Predicted vs Actual for the last 'days'.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    symbol = f"{coin}USDT"
    
    # Need to fetch enough data to calculate indicators (buffer) and lookback
    # Indicators like SMA50 lose 50 points. Lookback is 60.
    limit = 200 + days 
    df = fetch_klines(symbol, limit=limit)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Failed to fetch data")
        
    from src.evaluate import execute_rolling_backtest
    history = execute_rolling_backtest(symbol, df, days=days)
    
    if history is None:
        raise HTTPException(status_code=500, detail="Validation failed (Model missing or insufficient data)")
        
    if isinstance(history, dict) and "error" in history:
        raise HTTPException(status_code=400, detail=history["error"])
        
    return history

@router.post("/train/{coin}")
def train_model_endpoint(coin: str, background_tasks: BackgroundTasks):
    """
    Trigger a model retrain command for a specific coin.
    Processed in background to prevent timeouts.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    from src.train_model import train_single_coin
    
    background_tasks.add_task(train_single_coin, f"{coin}USDT")
    
    return {"status": "processing", "message": f"Training started for {coin}. Check back in 1-2 minutes."}

@router.get("/train-status/{coin}")
def get_training_status(coin: str):
    """
    Check the latest model version and timestamp to see if training completed.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    registry = ModelRegistry()
    latest_version = registry.get_latest_version(f"{coin}USDT")
    
    if latest_version == "v0.0.0":
        return {"status": "not_trained", "version": None, "timestamp": None}
        
    # Load metadata to get timestamp
    try:
        import os
        import json
        
        # We can use registry internal path logic or load_latest_model (but load is heavy)
        # Let's just peek at the file directly for speed
        model_dir = os.path.join("models", f"{coin}USDT", latest_version)
        meta_path = os.path.join(model_dir, "metadata.json")
        
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                metadata = json.load(f)
            return {
                "status": "trained", 
                "version": latest_version, 
                "timestamp": metadata.get("timestamp"),
                "metrics": metadata.get("metrics")
            }
    except:
        pass
        
    return {"status": "unknown", "version": latest_version}
