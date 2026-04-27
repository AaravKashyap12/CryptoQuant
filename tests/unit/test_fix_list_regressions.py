import inspect
import os
import time
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


class FixListRegressionTests(unittest.TestCase):
    def test_coin_config_uses_recent_regime_limits_and_capacity(self):
        from shared.ml.training import COIN_CONFIG

        self.assertEqual(COIN_CONFIG["BTC"]["limit"], 500)
        self.assertEqual(COIN_CONFIG["ETH"]["limit"], 500)
        self.assertEqual(COIN_CONFIG["SOL"]["limit"], 400)
        self.assertEqual(COIN_CONFIG["BNB"]["limit"], 350)
        self.assertEqual(COIN_CONFIG["ADA"]["limit"], 350)
        self.assertEqual(COIN_CONFIG["BNB"]["dropout_rate"], 0.4)
        self.assertEqual(COIN_CONFIG["ADA"]["units"], 64)
        self.assertEqual(COIN_CONFIG["BTC"]["units"], 128)

    def test_debug_defaults_to_false(self):
        from shared.core.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(Settings().DEBUG, False)

    def test_inr_conversion_rate_has_no_markup(self):
        from shared.utils import data_fetcher

        with patch.object(data_fetcher, "get_live_rate", lambda currency: 90.0):
            self.assertEqual(data_fetcher.get_conversion_rate("INR"), 90.0)

    def test_local_ohlcv_cache_sweeps_expired_entries(self):
        from shared.core import config as cfg_module
        from shared.utils import data_fetcher

        class FakeExchange:
            def fetch_ohlcv(self, pair, timeframe="1d", limit=500):
                base = pd.Timestamp("2025-01-01")
                return [
                    [
                        int((base + pd.Timedelta(days=i)).timestamp() * 1000),
                        100 + i,
                        101 + i,
                        99 + i,
                        100.5 + i,
                        1000 + i,
                    ]
                    for i in range(limit)
                ]

        with patch.object(cfg_module.settings, "USE_REDIS", False), patch.object(
            data_fetcher, "get_exchange_client", lambda exchange_id: FakeExchange()
        ):
            data_fetcher._LOCAL_OHLCV_CACHE.clear()
            data_fetcher._LOCAL_OHLCV_CACHE["expired"] = (time.time() - 1, pd.DataFrame())

            data_fetcher.fetch_klines("BTCUSDT", limit=10)

            self.assertNotIn("expired", data_fetcher._LOCAL_OHLCV_CACHE)

    def test_sentiment_is_neutralized_for_bnb_and_ada(self):
        from shared.utils.features import add_sentiment_indicators

        index = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({"close": [1, 2, 3]}, index=index)
        sentiment = pd.DataFrame({"sentiment_score": [91, 92, 93]}, index=index)

        result = add_sentiment_indicators(df, sentiment, coin="BNB")

        self.assertEqual(result["sentiment_score"].tolist(), [50.0, 50.0, 50.0])

    def test_get_latest_prediction_defaults_to_ten_mc_iterations(self):
        from shared.ml.predict import get_latest_prediction

        default = inspect.signature(get_latest_prediction).parameters["n_iter"].default
        self.assertEqual(default, 10)

    def test_evaluate_model_returns_directional_accuracy(self):
        from shared.ml.evaluate import evaluate_model

        class TensorLike:
            def __init__(self, values):
                self.values = values

            def numpy(self):
                return self.values

        class FakeModel:
            def __call__(self, X, training=True):
                return TensorLike(np.array([[0.55], [0.45], [0.75]]))

        scaler = MinMaxScaler()
        scaler.fit(np.array([[0.0], [100.0]]))

        metrics = evaluate_model(
            FakeModel(),
            np.zeros((3, 2, 1)),
            np.array([[0.50], [0.50], [0.70]]),
            scaler,
        )

        self.assertIn("directional_accuracy", metrics)
        self.assertGreaterEqual(metrics["directional_accuracy"], 0.0)
        self.assertLessEqual(metrics["directional_accuracy"], 1.0)

    def test_api_live_paths_use_coin_configured_fetch_limits(self):
        from services.api.routes import endpoints
        from shared.ml.training import COIN_CONFIG
        from shared.ml import cache as cache_module
        from shared.ml import evaluate as evaluate_module
        from shared.ml import predict as predict_module
        from shared.ml import registry as registry_module
        from shared.utils import data_fetcher

        calls = []
        df = pd.DataFrame(
            {
                "close": [1.0] * 10,
                "high": [1.0] * 10,
                "low": [1.0] * 10,
                "open": [1.0] * 10,
                "volume": [1.0] * 10,
            },
            index=pd.date_range("2025-01-01", periods=10, freq="D"),
        )

        class FakeRegistry:
            def get_cached_prediction(self, coin):
                return None

            def save_cached_prediction(self, coin, forecast, metadata):
                return None

        class FakeCache:
            def get(self, key):
                return None

            def set(self, key, value, ttl=None):
                return None

            def delete(self, key):
                return None

        def fake_fetch(symbol, limit=500, interval=None):
            calls.append((symbol, limit))
            return df

        with patch.object(cache_module, "cache", FakeCache()), patch.object(
            registry_module, "get_model_registry", lambda: FakeRegistry()
        ), patch.object(data_fetcher, "fetch_klines", fake_fetch), patch.object(
            predict_module,
            "get_latest_prediction",
            lambda coin, frame, n_iter=10: {
                "mean": np.array([1.0]),
                "lower": np.array([0.9]),
                "upper": np.array([1.1]),
                "metadata": {"version": "test"},
            },
        ), patch.object(
            evaluate_module, "execute_rolling_backtest", lambda coin, frame, days=30: []
        ):
            endpoints.predict_coin("BNB")
            endpoints.refresh_prediction("BNB", x_api_key=None)
            endpoints.validate_model_endpoint("BNB", days=30)

        self.assertEqual(calls[0], ("BNBUSDT", COIN_CONFIG["BNB"]["limit"]))
        self.assertEqual(calls[1], ("BNBUSDT", COIN_CONFIG["BNB"]["limit"]))
        self.assertEqual(calls[2], ("BNBUSDT", max(COIN_CONFIG["BNB"]["limit"], 230)))

    def test_training_split_fits_scalers_on_train_rows_only(self):
        from shared.ml.training import _prepare_time_series_splits

        periods = 220
        index = pd.date_range("2025-01-01", periods=periods, freq="D")
        values = np.arange(periods, dtype=float) + 100.0
        df = pd.DataFrame(
            {
                "close": values,
                "high": values + 1,
                "low": values - 1,
                "open": values - 0.5,
                "volume": np.linspace(1000, 2000, periods),
                "source": ["Unit"] * periods,
            },
            index=index,
        )

        X_train, y_train, X_val, y_val, X_test, y_test, scaler, _ = _prepare_time_series_splits(
            df,
            coin="BTC",
            lookback=20,
            forecast_horizon=7,
        )

        total = len(X_train) + len(X_val) + len(X_test)
        self.assertEqual(len(X_train), int(total * 0.7))
        self.assertEqual(len(X_val), int(total * 0.8) - int(total * 0.7))
        self.assertGreater(len(X_test), 0)
        self.assertLess(scaler.data_max_[0], df["close"].max())
        self.assertGreater(np.max(X_test[:, :, 0]), 1.0)


if __name__ == "__main__":
    unittest.main()
