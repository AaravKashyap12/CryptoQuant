from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
import pandas as pd
from shared.utils.data_fetcher import fetch_klines
# from shared.ml.predict import get_latest_prediction
from shared.ml.registry import ModelRegistry
from shared.ml.evaluate import execute_rolling_backtest
from shared.ml.predict import predict_with_uncertainty
from shared.utils.preprocess import prepare_inference_data

router = APIRouter()

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]

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
        
    try:
        symbol = f"{coin}USDT"
        df = fetch_klines(symbol, limit=limit)
        
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch data from Binance (Returned None)")
            
        # Convert to JSON-compatible format
        df.index.name = "open_time"
        df.reset_index(inplace=True) 
        
        import numpy as np
        
        if 'open_time' in df.columns:
            df['open_time'] = pd.to_datetime(df['open_time'])
            df['open_time'] = df['open_time'].astype('datetime64[ns]').astype(np.int64) // 10**6
            
        return df.to_dict(orient="records")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Market Data Error: {str(e)}")

@router.post("/predict/{coin}")
def predict_coin(coin: str):
    """
    Generate 7-day price forecast with confidence intervals.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")

    symbol = f"{coin}USDT"
        
    try:
        from shared.ml.predict import get_latest_prediction
        df = fetch_klines(symbol, limit=500)
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch data needed for prediction")
        
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")

@router.get("/metrics/{coin}")
def get_model_metrics(coin: str):
    """
    Get the latest model health metrics from the registry.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    symbol = f"{coin}USDT"
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
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
    limit = 200 + days 
    df = fetch_klines(symbol, limit=limit)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Failed to fetch data")
        
    from shared.ml.evaluate import execute_rolling_backtest
    history = execute_rolling_backtest(symbol, df, days=days)
    
    if history is None:
        raise HTTPException(status_code=500, detail="Validation failed (Model missing or insufficient data)")
        
    if isinstance(history, dict) and "error" in history:
        raise HTTPException(status_code=400, detail=history["error"])
        
    return history

@router.get("/validate/{coin}")
def validate_model_endpoint(coin: str):
    """
    Check the latest model version and history for validation charts.
    """
    if coin not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
        
    symbol = f"{coin}USDT"
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    
    meta = registry.get_latest_version_metadata(symbol)
    
    if not meta:
        return {"status": "not_trained", "version": None, "timestamp": None}
        
    return {
        "status": "trained", 
        "version": meta.get("version"), 
        "timestamp": meta.get("created_at"),
        "metrics": meta.get("metrics")
    }

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
        from shared.utils.data_fetcher import fetch_klines
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
        from shared.ml.registry import ModelRegistry
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
                         from shared.ml.predict import predict_with_uncertainty
                         from shared.utils.preprocess import prepare_inference_data
                         
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

@router.get("/debug/data/{coin}")
def debug_data_values(coin: str):
    """
    Inspect the raw data values to debug 1970 date issue.
    """
    symbol = f"{coin}USDT"
    df = fetch_klines(symbol, limit=5)
    
    if df is None:
        return {"error": "Could not fetch data"}
        
    debug_info = {
        "source": df.iloc[-1].get('source', 'unknown') if 'source' in df.columns else 'unknown',
        "index_name": df.index.name,
        "index_dtype": str(df.index.dtype),
        "sample_index": str(df.index[0]),
        "columns": list(df.columns)
    }
    
    # Test Conversion Logic
    df_test = df.copy()
    df_test.index.name = "open_time"
    df_test.reset_index(inplace=True)
    
    debug_info["col_dtype_before"] = str(df_test['open_time'].dtype)
    debug_info["val_before_0"] = str(df_test['open_time'].iloc[0])
    
    # Perform conversion exactly as in market-data
    import numpy as np
    try:
        converted = df_test['open_time'].astype(np.int64) // 10**6
        debug_info["val_after_0"] = int(converted.iloc[0])
        debug_info["expected_year"] = pd.to_datetime(converted.iloc[0], unit='ms').year
    except Exception as e:
        debug_info["conversion_error"] = str(e)
        
    return debug_info
