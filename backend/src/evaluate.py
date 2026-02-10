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
    required_len = lookback + days + forecast_horizon
    if len(df) < required_len:
        return {"error": f"Not enough data. Need {required_len}, have {len(df)}"}
        
    # Process Data
    df_full = add_technical_indicators(df.copy())
    feature_cols = get_feature_columns()
    
    # Scale
    data_values = df_full[feature_cols].values
    scaled_data = scaler.transform(data_values)
    
    # We want to predict for the LAST 'days' days.
    # Use df_full length because indicators dropped rows.
    
    history = []
    
    end_idx = len(df_full) 
    start_idx = end_idx - days
    
    for i in range(start_idx, end_idx):
        # Input for prediction at index 'i' in df_full
        # This matches scaled_data[i]

        # No, to predict price at 'i', we need data ending at 'i-1'.
        
        # Slice: [i-lookback : i] -> Predictions for 'i' (technically i+1 if we predict next step)
        # Wait, standard LSTM: Input [t-L : t] -> Output [t+1]
        
        # Let's say current time is 'i'. We want to know what the model *would have* predicted for 'i'.
        # So we feed [i-lookback-1 : i-1].
        
        # Input range
        input_start = i - lookback
        input_end = i
        
        if input_start < 0: continue
            
        X = scaled_data[input_start : input_end]
        X = X.reshape(1, lookback, X.shape[1])
        
        # Run inference
        y_pred_scaled = model.predict(X, verbose=0)
        
        # Inverse transform (Output shape is 1, 7)
        y_pred = target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
        
        # Actual price at 'i' (We want to compare t+1 prediction with t+1 actual)
        # But our model predicts 7 steps.
        # Let's just take the 1st step prediction (t+1) and compare with Actual at t+1.
        # So if input ends at 'i', prediction is for 'i+1'?
        # My model is trained to predict [t+1, t+2, ... t+7] given [t-L ... t].
        # So if I feed data up to index 'i', I get prediction for 'i+1'.
        
        # But loop 'i' is the index of the day we want to visualize.
        # So actual is df.iloc[i].close.
        # To predict for 'i', we needed data ending at 'i-1'.
        
        # Correct logic:
        # We want to visualize comparison at index 'i'.
        # Actual = df.iloc[i].close
        # Prediction Input = df.iloc[i-lookback : i] (Data BEFORE i)
        
        # Wait, if I supply [0...59], I predict 60.
        # So if I want prediction for 'i', I input [i-lookback : i]. No, that includes 'i'. 
        # I need [i-lookback : i].
        
        # Let's verify shape.
        # scaled_data[i] is the data vector for time 'i'.
        # If I want to predict price at 'i', I should not know price at 'i'.
        # So input should end at 'i'.
        # The slice [start:end] excludes end.
        # So scaled_data[i-lookback : i] contains indices i-lookback ... i-1.
        # Correct. This inputs past data to predict 'i'.
        
        # But wait, my model output is 7 steps starting from t+1.
        # If input is [t-L ... t], output is t+1...
        # So input [i-lookback : i] (ending at i-1) -> Predicts 'i'.
        
        # Yes.
        
        # Actual
        # df_full has indices reset or continuous?
        # df_full is a copy of df with dropped na.
        actual_price = df_full.iloc[i]['close']
        timestamp = df_full.index[i]
        
        date_str = str(timestamp)
        
        history.append({
            "date": date_str,
            "actual": float(actual_price),
            "predicted": float(y_pred[0]) # 1st step forecast
        })
        
    return history

