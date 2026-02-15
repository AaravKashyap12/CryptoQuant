import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
from src.registry import ModelRegistry
from src.preprocess import prepare_inference_data

def naive_baseline(data, forecast_horizon):
    """
    Predicts the last value for all future steps.
    """
    last_val = data[-1]
    return np.full(forecast_horizon, last_val)

def execute_rolling_backtest(coin, df, days=30, forecast_horizon=7):
    """
    Performs a rolling backtest for the API.
    Returns a list of {date, actual, predicted} for the visualization.
    """
    from src.registry import ModelRegistry
    from src.features import add_technical_indicators, get_feature_columns
    
    registry = ModelRegistry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)
    
    if model is None:
        return None
        
    lookback = metadata['config']['lookback']
    
    # Ensure enough data
    # Indicators lose data, so we need a buffer
    required_len = lookback + days + forecast_horizon + 50 
    if len(df) < required_len:
        # Try with what we have, add_technical_indicators will drop NAs
        pass
        
    # Process Data
    df_full = add_technical_indicators(df.copy())
    feature_cols = get_feature_columns()
    
    # Drop rows with NAs from indicators
    df_full.dropna(inplace=True)
    
    if len(df_full) < (lookback + days):
         return {"error": f"Not enough data after indicators. Need {lookback + days}, have {len(df_full)}"}

    # Scale
    data_values = df_full[feature_cols].values
    scaled_data = scaler.transform(data_values)
    
    history = []
    
    # We want the last 'days' points
    end_idx = len(df_full) 
    start_idx = end_idx - days
    
    for i in range(start_idx, end_idx):
        # Input for prediction at index 'i'
        # Data BEFORE i: [i-lookback : i]
        input_start = i - lookback
        input_end = i
        
        if input_start < 0: continue
            
        X = scaled_data[input_start : input_end]
        X = X.reshape(1, lookback, X.shape[1])
        
        # Run inference
        y_pred_scaled = model.predict(X, verbose=0)
        
        # Inverse transform
        y_pred = target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
        
        # Actual price at 'i'
        actual_price = df_full.iloc[i]['close']
        timestamp = df_full.index[i]
        
        history.append({
            "date": str(timestamp),
            "actual": float(actual_price),
            "predicted": float(y_pred[0]) # 1st step forecast (t+1)
        })
        
    return history

def rolling_backtest(coin, df, days=30, forecast_horizon=7):
    """
    Performs a rolling backtest over the last 'days'.
    
    Args:
        coin (str): Coin symbol.
        df (pd.DataFrame): Historical data.
        days (int): Number of days to backtest (e.g. 30).
        forecast_horizon (int): Prediction steps.
        
    Returns:
        results (pd.DataFrame): Actual vs Predicted for each step.
        metrics (dict): RMSE/MAE for Model vs Baseline.
    """
    registry = ModelRegistry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)
    
    if model is None:
        return None, None
        
    lookback = metadata['config']['lookback']
    
    # We need enough data: lookback + days + forecast_horizon (to have actuals)
    min_len = lookback + days + forecast_horizon
    if len(df) < min_len:
        print(f"Not enough data for backtest. Need {min_len}, have {len(df)}")
        return None, None
        
    # Start index for the backtest loop
    # We want the loop to end such that we have actuals for the forecast
    # End of data is index N-1
    # Last possible start point is N - forecast_horizon
    # We want 'days' number of start points
    
    end_idx = len(df) - forecast_horizon
    start_idx = end_idx - days
    
    predictions = []
    actuals = []
    baselines = []
    dates = []
    
    # Add Technical Indicators ONCE to the whole dataframe
    # But wait, prepare_inference_data adds them inside. 
    # That might be inefficient but safe to prevent lookahead bias if indicators use future data (they shouldn't).
    # Ideally indicators are lagging constraints.
    # To be strictly safe, we should pass the slice to prepare_inference_data.
    
    from src.features import add_technical_indicators
    # Optimization: Calculate indicators once
    df_full = add_technical_indicators(df.copy())
    
    # We need to manually scale because prepare_inference_data does fit_transform or transform?
    # It does transform.
    
    from src.features import get_feature_columns
    feature_cols = get_feature_columns()
    data_values = df_full[feature_cols].values
    scaled_data = scaler.transform(data_values)
    
    # Target (close) index
    target_idx = feature_cols.index('close')
    
    for i in range(start_idx, end_idx):
        # Input: [i-lookback : i]
        X = scaled_data[i-lookback:i]
        X = X.reshape(1, lookback, X.shape[1])
        
        # Actual: [i : i+forecast_horizon] (Close price)
        # We need unscaled actuals
        # Scale back? Or use raw df bytes?
        # Let's use raw df
        y_true = df.iloc[i:i+forecast_horizon]['close'].values
        
        # Predict
        y_pred_scaled = model.predict(X, verbose=0)
        
        # Inverse
        y_pred = target_scaler.inverse_transform(y_pred_scaled).flatten()
        
        # Baseline
        # Last known close is at index i-1
        last_close = df.iloc[i-1]['close']
        y_base = np.full(forecast_horizon, last_close)
        
        predictions.append(y_pred)
        actuals.append(y_true)
        baselines.append(y_base)
        dates.append(df.index[i])
        
    # Calculate Overall Metrics (Flattened)
    flat_pred = np.concatenate(predictions)
    flat_true = np.concatenate(actuals)
    flat_base = np.concatenate(baselines)
    
    rmse_model = np.sqrt(mean_squared_error(flat_true, flat_pred))
    mae_model = mean_absolute_error(flat_true, flat_pred)
    
    rmse_base = np.sqrt(mean_squared_error(flat_true, flat_base))
    mae_base = mean_absolute_error(flat_true, flat_base)
    
    metrics = {
        "Model RMSE": rmse_model,
        "Model MAE": mae_model,
        "Baseline RMSE": rmse_base,
        "Baseline MAE": mae_base,
        "Improvement (%)": ((mae_base - mae_model) / mae_base) * 100
    }
    
    # Return last forecast comparison for visualization
    results = pd.DataFrame({
        "Date": pd.date_range(start=dates[-1], periods=forecast_horizon),
        "Actual": actuals[-1],
        "Predicted": predictions[-1],
        "Baseline": baselines[-1]
    })
    
    return results, metrics
