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
    # Ensure index is named "open_time" so it becomes a column with that name
    df.index.name = "open_time"
    df.reset_index(inplace=True) # Make timestamp a column
    
    # Ensure date is UNIX timestamp (ms) to avoid JS parsing issues ("Invalid Date")
    import numpy as np
    # Convert 'open_time' column (which we just created) to int64 milliseconds
    if 'open_time' in df.columns:
        df['open_time'] = df['open_time'].astype(np.int64) // 10**6
        
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

@router.get("/debug/system")
def system_diagnostics():
    """
    Run a self-test of the system components.
    """
    report = {"status": "ok", "steps": {}}
    
    # 1. System Info
    import sys
    import platform
    report["steps"]["system"] = {
        "python": sys.version,
        "platform": platform.platform()
    }
    
    # 2. TensorFlow Check
    try:
        import tensorflow as tf
        report["steps"]["tensorflow"] = {
            "status": "ok", 
            "version": tf.__version__,
            "gpu_available": len(tf.config.list_physical_devices('GPU')) > 0
        }
    except Exception as e:
        report["steps"]["tensorflow"] = {"status": "failed", "error": str(e)}
        report["status"] = "degraded"
        
    # 3. Data Fetcher Check
    try:
        from src.data_fetcher import fetch_klines
        df = fetch_klines("BTCUSDT", limit=10)
        if df is not None:
             report["steps"]["data_fetcher"] = {
                 "status": "ok", 
                 "source": df.iloc[-1].get('source', 'unknown'),
                 "rows": len(df)
             }
        else:
             report["steps"]["data_fetcher"] = {"status": "failed", "error": "returned None"}
             report["status"] = "degraded"
    except Exception as e:
        report["steps"]["data_fetcher"] = {"status": "failed", "error": str(e)}
        report["status"] = "degraded"
        
    # 4. Model Registry Check
    try:
        from src.registry import ModelRegistry
        registry = ModelRegistry()
        v = registry.get_latest_version("BTCUSDT")
        report["steps"]["model_registry"] = {"latest_btc_version": v}
        
        if v != "v0.0.0":
            # Try Loading (This is the critical crash point usually)
            try:
                model, _, _, _ = registry.load_latest_model("BTCUSDT")
                if model:
                     report["steps"]["model_load"] = {"status": "ok"}
                     
                     # 5. Test Inference (The Real Test)
                     try:
                         # Create Dummy Data (matches Mock data structure)
                         import pandas as pd
                         import numpy as np
                         from src.predict import predict_with_uncertainty
                         from src.preprocess import prepare_inference_data
                         
                         dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
                         dummy_df = pd.DataFrame({
                             'open_time': dates,
                             'open': np.random.rand(100) * 1000,
                             'high': np.random.rand(100) * 1000,
                             'low': np.random.rand(100) * 1000,
                             'close': np.random.rand(100) * 1000,
                             'volume': np.random.rand(100) * 10000
                         })
                         dummy_df.set_index('open_time', inplace=True)
                         
                         # Preprocess
                         X_input = prepare_inference_data(dummy_df, scaler=registry.load_latest_model("BTCUSDT")[1], lookback=60)
                         report["steps"]["preprocess"] = {"status": "ok", "shape": str(X_input.shape)}
                         
                         # Predict
                         mean, _, _ = predict_with_uncertainty(model, X_input, n_iter=2)
                         report["steps"]["inference"] = {"status": "ok", "output_shape": str(mean.shape)}
                         
                     except Exception as e:
                         import traceback
                         report["steps"]["inference"] = {"status": "failed", "error": str(e), "trace": traceback.format_exc()}
                         
                else:
                     report["steps"]["model_load"] = {"status": "failed_return_none"}
            except Exception as e:
                 report["steps"]["model_load"] = {"status": "crashed", "error": str(e)}
    except Exception as e:
        report["steps"]["model_registry"] = {"status": "failed", "error": str(e)}
        
    return report
