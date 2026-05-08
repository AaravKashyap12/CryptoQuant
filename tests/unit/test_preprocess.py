import unittest

import numpy as np
import pandas as pd

from shared.utils.features import (
    add_market_context_indicators,
    add_sentiment_indicators,
    add_technical_indicators,
    get_feature_columns,
)
from shared.utils.preprocess import prepare_inference_data, prepare_training_data


def make_df(periods=150):
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="D")
    return pd.DataFrame(
        {
            "open": np.random.rand(periods) * 100,
            "high": np.random.rand(periods) * 100,
            "low": np.random.rand(periods) * 100,
            "close": np.random.rand(periods) * 100,
            "volume": np.random.rand(periods) * 1000,
        },
        index=dates,
    )


class PreprocessTests(unittest.TestCase):
    def test_technical_indicators(self):
        df = make_df(100)
        df_out = add_technical_indicators(df)
        df_out = add_market_context_indicators(df_out, None)

        self.assertIn("rsi", df_out.columns)
        self.assertIn("MACD_12_26_9", df_out.columns)
        self.assertIn("MACDh_12_26_9", df_out.columns)
        self.assertIn("MACDs_12_26_9", df_out.columns)
        self.assertIn("ema_7", df_out.columns)
        self.assertIn("ema_25", df_out.columns)
        self.assertIn("ema_50", df_out.columns)
        self.assertIn("atr", df_out.columns)
        self.assertIn("vol_ma_20", df_out.columns)
        self.assertIn("funding_rate", df_out.columns)
        self.assertIn("open_interest", df_out.columns)
        self.assertIn("open_interest_change", df_out.columns)

        tail = df_out.tail(50)[["rsi", "MACD_12_26_9", "ema_50", "atr", "vol_ma_20"]]
        self.assertFalse(tail.isnull().any().any())

    def test_prepare_training_data(self):
        df = make_df(150)
        X, y, scaler, target_scaler = prepare_training_data(df, lookback=10, forecast_horizon=3)

        self.assertEqual(X.ndim, 3)
        self.assertEqual(X.shape[1], 10)
        self.assertEqual(y.shape[1], 3)
        self.assertEqual(len(X), len(y))
        self.assertEqual(X.shape[2], 18)

    def test_log_volume_scaling_is_consistent_between_train_and_inference(self):
        df = make_df(150)
        _, _, scaler, _ = prepare_training_data(df, lookback=10, forecast_horizon=3)
        X_infer = prepare_inference_data(df, scaler, lookback=10)

        engineered = add_market_context_indicators(
            add_sentiment_indicators(add_technical_indicators(df), None),
            None,
        )
        feature_cols = get_feature_columns()
        engineered = engineered.dropna(subset=feature_cols)
        expected_last_window = scaler.transform(engineered[feature_cols].values)[-10:]

        np.testing.assert_allclose(expected_last_window, X_infer[0])


if __name__ == "__main__":
    unittest.main()
