import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from shared.utils.features import add_technical_indicators, get_feature_columns, add_sentiment_indicators

def create_scaler():
    """
    Create a MinMaxScaler for normalizing data.
    """
    return MinMaxScaler(feature_range=(0, 1))

def prepare_training_data(
    df,
    lookback=60,
    target_col='close',
    forecast_horizon=1,
    sentiment_df=None,
    coin=None,
    scaler=None,
    target_scaler=None,
    fit_scalers=True,
):
    """
    Prepare data for LSTM model training with MULTIPLE features.
    
    Args:
        df (pd.DataFrame): Dataframe with price data.
        lookback (int): Number of past days to use for prediction.
        target_col (str): Column to predict (usually 'close').
        forecast_horizon (int): Number of days to predict into the future.
        sentiment_df (pd.DataFrame): Optional sentiment data.
        
    Returns:
        X (np.array): Input sequences [samples, lookback, n_features].
        y (np.array): Target values [samples, forecast_horizon].
        scaler (MinMaxScaler): Fitted scaler for the FEATURES.
        target_scaler (MinMaxScaler): Fitted scaler for the TARGET (for inverse transform).
    """
    # 1. Add Indicators
    df = add_technical_indicators(df)
    df = add_sentiment_indicators(df, sentiment_df, coin=coin)

    # 2. Select Features
    feature_cols = get_feature_columns()
    
    # FIX: Drop NaN rows BEFORE fitting scalers.
    # Technical indicators (MACD needs ~26 periods, Bollinger ~20) produce NaN
    # for the first N rows. If these rows are included when fitting target_scaler,
    # the scaler's min/max is anchored to older/lower prices, causing
    # systematic underestimation (~$15k gap) at inference time.
    # Dropna only based on feature columns so we don't accidentally drop valid data where `source` is NaN.
    df = df.dropna(subset=feature_cols)

    data = df[feature_cols].values
    target = df[[target_col]].values
    
    # 3. Fit Scalers (now on clean, NaN-free data)
    if scaler is None:
        scaler = create_scaler()
    if target_scaler is None:
        target_scaler = create_scaler()

    if fit_scalers:
        scaled_data = scaler.fit_transform(data)
        scaled_target = target_scaler.fit_transform(target)
    else:
        scaled_data = scaler.transform(data)
        scaled_target = target_scaler.transform(target)
    
    X, y = [], []
    
    # 5. Create Sequences
    # We need 'lookback' steps for X, and 'forecast_horizon' steps for y
    for i in range(lookback, len(scaled_data) - forecast_horizon + 1):
        # Input: [i-lookback : i] (All features)
        X.append(scaled_data[i-lookback:i])
        
        # Target: [i : i+forecast_horizon] (Scaled 'close' price ONLY)
        # Using scaled_target ensures it's perfectly invertible by target_scaler
        target_seq = scaled_target[i : i+forecast_horizon, 0]
        y.append(target_seq)
        
    X, y = np.array(X), np.array(y)
    
    return X, y, scaler, target_scaler

def prepare_inference_data(df, scaler, lookback=60, sentiment_df=None, coin=None):
    """
    Prepare data for inference (last sequence).
    """
    # 1. Add Indicators
    df.index.name = "open_time"
    df = add_technical_indicators(df)
    df = add_sentiment_indicators(df, sentiment_df, coin=coin)

    # FIX: Drop NaN rows so the scaler.transform sees the same feature
    # distribution it was fitted on during training.
    df = df.dropna()
    
    # 2. Select Features
    feature_cols = get_feature_columns()
    data = df[feature_cols].values

    # FIX: Guard against feature count mismatch between train and inference.
    # A silent shape mismatch produces wrong scaled values without raising an error.
    expected_features = scaler.n_features_in_
    if data.shape[1] != expected_features:
        raise ValueError(
            f"Feature count mismatch: scaler expects {expected_features} features, "
            f"but inference data has {data.shape[1]}. "
            f"Re-check get_feature_columns() consistency between training and inference."
        )
    
    # 3. Scale
    scaled_data = scaler.transform(data)
    
    # 4. Get last sequence
    if len(scaled_data) < lookback:
        raise ValueError(f"Insufficient data for inference. Needed {lookback}, got {len(scaled_data)}")

    last_sequence = scaled_data[-lookback:]
    
    # Reshape for LSTM [1, lookback, n_features]
    X = np.reshape(last_sequence, (1, lookback, last_sequence.shape[1]))
    
    return X
