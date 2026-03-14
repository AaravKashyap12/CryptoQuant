import os
import sys
import pandas as pd
import numpy as np
sys.path.append(os.getcwd())
from shared.utils.data_fetcher import fetch_klines, fetch_sentiment_data
from shared.utils.features import add_technical_indicators, add_sentiment_indicators, get_feature_columns
from shared.utils.preprocess import prepare_training_data

def investigate_btc():
    print("--- Investigating BTC Data and Scaling ---")
    df = fetch_klines("BTCUSDT", limit=1000)
    if df is None:
        print("Failed to fetch data")
        return

    print(f"Fetched {len(df)} rows from {df['source'].iloc[0]}")
    print(f"Price Min: {df['close'].min()}, Max: {df['close'].max()}, Mean: {df['close'].mean()}")

    # Check for gaps in index
    expected_range = pd.date_range(start=df.index[0], end=df.index[-1], freq='D')
    if len(df) != len(expected_range):
        print(f" [WARN] Found GAPS in data! Expected {len(expected_range)} days, got {len(df)}")
    
    sentiment_df = fetch_sentiment_data(limit=1000)
    
    # Run through full preprocessing
    X, y, scaler, target_scaler = prepare_training_data(df, lookback=60, forecast_horizon=7, sentiment_df=sentiment_df)
    
    print(f"Processed sequences: {len(X)}")
    print(f"Feature columns: {get_feature_columns()}")
    
    # Test inverse transform manually
    test_val = df['close'].iloc[-1]
    scaled_val = target_scaler.transform([[test_val]])[0][0]
    inv_val = target_scaler.inverse_transform([[scaled_val]])[0][0]
    print(f"Scaling Test: Original={test_val}, Scaled={scaled_val:.6f}, Inverted={inv_val}")
    
    if abs(test_val - inv_val) > 1.0:
        print(" [ERROR] TARGET SCALING IS BROKEN!")
    else:
        print(" [OK] Target scaling is consistent.")

    # Check for outliers in features
    df_feat = add_technical_indicators(df)
    df_feat = add_sentiment_indicators(df_feat, sentiment_df)
    for col in get_feature_columns():
        if col in df_feat.columns:
            c_min, c_max = df_feat[col].min(), df_feat[col].max()
            if np.isinf(c_min) or np.isinf(c_max):
                print(f" [CRITICAL] Infinity found in column {col}!")
            if df_feat[col].isna().sum() > 0:
                print(f" [WARN] NaNs found in column {col} count: {df_feat[col].isna().sum()}")

investigate_btc()
