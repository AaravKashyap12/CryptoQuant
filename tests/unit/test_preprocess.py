import pytest
import pandas as pd
import numpy as np
from shared.utils.features import add_technical_indicators
from shared.utils.preprocess import prepare_training_data

def test_technical_indicators():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.random.rand(100) * 100,
        "high": np.random.rand(100) * 100,
        "low": np.random.rand(100) * 100,
        "close": np.random.rand(100) * 100,
        "volume": np.random.rand(100) * 1000
    }, index=dates)
    
    df_indicators = add_technical_indicators(df)
    assert "rsi" in df_indicators.columns
    assert "MACD_12_26_9" in df_indicators.columns
    # Indicators have lag (NaNs), but add_technical_indicators should drop them
    assert not df_indicators.isnull().any().any()

def test_prepare_training_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.random.rand(100) * 100,
        "high": np.random.rand(100) * 100,
        "low": np.random.rand(100) * 100,
        "close": np.random.rand(100) * 100,
        "volume": np.random.rand(100) * 1000
    }, index=dates)
    
    X, y, scaler, target_scaler = prepare_training_data(df, lookback=10, forecast_horizon=3)
    
    assert X.ndim == 3 # [Samples, Lookback, Features]
    assert X.shape[1] == 10
    assert y.shape[1] == 3
    assert len(X) == len(y)
