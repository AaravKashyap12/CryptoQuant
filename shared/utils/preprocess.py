import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from shared.utils.features import add_technical_indicators, get_feature_columns

def create_scaler():
    """
    Create a MinMaxScaler for normalizing data.
    """
    return MinMaxScaler(feature_range=(0, 1))

def prepare_training_data(df, lookback=60, target_col='close', forecast_horizon=1):
    """
    Prepare data for LSTM model training with MULTIPLE features.
    
    Args:
        df (pd.DataFrame): Dataframe with price data.
        lookback (int): Number of past days to use for prediction.
        target_col (str): Column to predict (usually 'close').
        forecast_horizon (int): Number of days to predict into the future.
        
    Returns:
        X (np.array): Input sequences [samples, lookback, n_features].
        y (np.array): Target values [samples, forecast_horizon].
        scaler (MinMaxScaler): Fitted scaler for the FEATURES.
        target_scaler (MinMaxScaler): Fitted scaler for the TARGET (for inverse transform).
    """
    # 1. Add Technical Indicators
    df = add_technical_indicators(df)
    
    # 2. Select Features
    feature_cols = get_feature_columns()
    data = df[feature_cols].values
    target = df[[target_col]].values
    
    # 3. Scale Features
    scaler = create_scaler()
    scaled_data = scaler.fit_transform(data)
    
    # 4. Scale Target (separately, for easy inverse transform)
    target_scaler = create_scaler()
    target_scaler.fit(target)
    # Note: 'close' is inside 'data', so it's scaled there too. 
    # We use target_scaler ONLY for inverting predictions later.
    
    X, y = [], []
    
    # 5. Create Sequences
    # We need 'lookback' steps for X, and 'forecast_horizon' steps for y
    for i in range(lookback, len(scaled_data) - forecast_horizon + 1):
        # Input: [i-lookback : i] (All features)
        X.append(scaled_data[i-lookback:i])
        
        # Target: [i : i+forecast_horizon] (Close price only, scaled)
        # We need to get the Scaled Target value. 
        # Since 'close' is the first column in feature_cols (usually), we can take it from scaled_data?
        # BETTER: Use separate scaling for target to be safe.
        # But 'close' is part of the features.
        # Let's align them.
        
        # Find index of target_col in feature_cols
        target_idx = feature_cols.index(target_col)
        
        # y sequence
        y.append(scaled_data[i:i+forecast_horizon, target_idx])
        
    X, y = np.array(X), np.array(y)
    
    return X, y, scaler, target_scaler

def prepare_inference_data(df, scaler, lookback=60):
    """
    Prepare data for inference (last sequence).
    """
    # 1. Add Indicators
    df = add_technical_indicators(df)
    
    # 2. Select Features
    feature_cols = get_feature_columns()
    data = df[feature_cols].values
    
    # 3. Scale
    scaled_data = scaler.transform(data)
    
    # 4. Get last sequence
    if len(scaled_data) < lookback:
        raise ValueError(f"Insufficient data for inference. Needed {lookback}, got {len(scaled_data)}")

    last_sequence = scaled_data[-lookback:]
    
    # Reshape for LSTM [1, lookback, n_features]
    X = np.reshape(last_sequence, (1, lookback, last_sequence.shape[1]))
    
    return X
