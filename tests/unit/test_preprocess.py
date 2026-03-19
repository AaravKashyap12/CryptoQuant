import pytest
import pandas as pd
import numpy as np
from shared.utils.features import add_technical_indicators
from shared.utils.preprocess import prepare_training_data


def make_df(periods=150):
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="D")
    return pd.DataFrame({
        "open":   np.random.rand(periods) * 100,
        "high":   np.random.rand(periods) * 100,
        "low":    np.random.rand(periods) * 100,
        "close":  np.random.rand(periods) * 100,
        "volume": np.random.rand(periods) * 1000,
    }, index=dates)


def test_technical_indicators():
    df = make_df(100)
    df_out = add_technical_indicators(df)

    # All expected columns are present
    assert "rsi"           in df_out.columns
    assert "MACD_12_26_9"  in df_out.columns
    assert "MACDh_12_26_9" in df_out.columns
    assert "MACDs_12_26_9" in df_out.columns
    assert "ema_7"         in df_out.columns
    assert "ema_25"        in df_out.columns
    assert "ema_50"        in df_out.columns
    assert "atr"           in df_out.columns
    assert "vol_ma_20"     in df_out.columns

    # NaNs are EXPECTED for warmup rows — dropna is done in preprocess, not here
    # Just check the tail rows (after warmup) are clean
    assert not df_out.tail(50)[["rsi", "MACD_12_26_9", "ema_50", "atr", "vol_ma_20"]].isnull().any().any()


def test_prepare_training_data():
    df = make_df(150)
    X, y, scaler, target_scaler = prepare_training_data(df, lookback=10, forecast_horizon=3)

    assert X.ndim == 3          # (samples, lookback, features)
    assert X.shape[1] == 10     # lookback window
    assert y.shape[1] == 3      # forecast horizon
    assert len(X) == len(y)     # aligned
    assert X.shape[2] == 15     # 15 features