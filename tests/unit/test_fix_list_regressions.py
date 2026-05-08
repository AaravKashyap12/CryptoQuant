import inspect
import os
import time
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


class FixListRegressionTests(unittest.TestCase):
    def test_forecast_horizon_is_shortened_to_one_day(self):
        from shared.ml import training

        self.assertEqual(training.FORECAST_HORIZON, 1)

    def test_coin_config_uses_expanded_history_and_capacity(self):
        from shared.ml.training import COIN_CONFIG

        self.assertEqual(COIN_CONFIG["BTC"]["limit"], 5000)
        self.assertEqual(COIN_CONFIG["ETH"]["limit"], 5000)
        self.assertEqual(COIN_CONFIG["SOL"]["limit"], 5000)
        self.assertEqual(COIN_CONFIG["BNB"]["limit"], 5000)
        self.assertEqual(COIN_CONFIG["ADA"]["limit"], 5000)
        self.assertGreaterEqual(COIN_CONFIG["BNB"]["lookback"], 30)
        self.assertEqual(COIN_CONFIG["BNB"]["dropout_rate"], 0.35)
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

    def test_fetch_klines_does_not_mock_by_default(self):
        from shared.core import config as cfg_module
        from shared.utils import data_fetcher

        with patch.object(cfg_module.settings, "USE_REDIS", False), patch.object(
            cfg_module.settings, "ALLOW_MOCK_DATA", False
        ), patch.object(data_fetcher, "get_exchange_client", lambda exchange_id: None):
            data_fetcher._LOCAL_OHLCV_CACHE.clear()
            df = data_fetcher.fetch_klines("BTCUSDT", limit=10)

        self.assertIsNone(df)

    def test_fetch_klines_can_mock_when_explicitly_allowed(self):
        from shared.core import config as cfg_module
        from shared.utils import data_fetcher

        with patch.object(cfg_module.settings, "USE_REDIS", False), patch.object(
            data_fetcher, "get_exchange_client", lambda exchange_id: None
        ):
            data_fetcher._LOCAL_OHLCV_CACHE.clear()
            df = data_fetcher.fetch_klines("BTCUSDT", limit=10, allow_mock=True)

        self.assertEqual(df["source"].iloc[0], "Mock")

    def test_data_availability_flags_recent_date_gaps(self):
        from local_train import _continuity_summary

        index = pd.to_datetime(
            ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06"]
        )
        df = pd.DataFrame({"close": [1, 2, 3, 4]}, index=index)

        summary, has_tail_gap = _continuity_summary(df)

        self.assertTrue(has_tail_gap)
        self.assertIn("tail_max_gap=3.0d", summary)

    def test_sentiment_applies_to_bnb_and_ada(self):
        from shared.utils.features import add_sentiment_indicators

        index = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({"close": [1, 2, 3]}, index=index)
        sentiment = pd.DataFrame({"sentiment_score": [91, 92, 93]}, index=index)

        result = add_sentiment_indicators(df, sentiment, coin="BNB")

        self.assertEqual(result["sentiment_score"].tolist(), [91, 92, 93])

    def test_feature_columns_include_market_context(self):
        from shared.utils.features import get_feature_columns

        feature_cols = get_feature_columns()
        self.assertIn("funding_rate", feature_cols)
        self.assertIn("open_interest", feature_cols)
        self.assertIn("open_interest_change", feature_cols)
        self.assertEqual(len(feature_cols), 18)

    def test_get_latest_prediction_defaults_to_fifty_mc_iterations(self):
        from shared.ml.predict import get_latest_prediction

        default = inspect.signature(get_latest_prediction).parameters["n_iter"].default
        self.assertEqual(default, 50)

    def test_get_latest_prediction_clamps_legacy_model_outputs_to_one_day(self):
        from shared.ml import predict as predict_module
        from shared.ml import registry as registry_module
        from shared.ml import monitoring as monitoring_module
        from shared.utils import data_fetcher

        index = pd.date_range("2025-01-01", periods=80, freq="D")
        df = pd.DataFrame(
            {
                "open": np.linspace(100, 180, len(index)),
                "high": np.linspace(101, 181, len(index)),
                "low": np.linspace(99, 179, len(index)),
                "close": np.linspace(100, 180, len(index)),
                "volume": np.linspace(1000, 2000, len(index)),
            },
            index=index,
        )

        class FakeModel:
            input_shape = (None, 60, 15)
            output_shape = (None, 7)

        class FakeScaler:
            n_features_in_ = 15

        class FakeTargetScaler:
            def inverse_transform(self, values):
                return values

        class FakeRegistry:
            def load_latest_model(self, coin):
                return FakeModel(), FakeScaler(), FakeTargetScaler(), {
                    "version": "legacy",
                    "config": {"lookback": 60, "features": 15},
                }

            def load_latest_aux_artifact(self, coin, filename):
                return None

        with patch.object(predict_module, "get_model_registry", lambda: FakeRegistry()), patch.object(
            predict_module, "prepare_inference_data", lambda *args, **kwargs: np.zeros((1, 60, 15))
        ), patch.object(
            predict_module, "predict_with_uncertainty", lambda model, X, n_iter=50: (
                np.array([1, 2, 3, 4, 5, 6, 7], dtype=float),
                np.array([0, 1, 2, 3, 4, 5, 6], dtype=float),
                np.array([2, 3, 4, 5, 6, 7, 8], dtype=float),
            )
        ), patch.object(
            data_fetcher, "fetch_sentiment_data", lambda limit=500: None
        ), patch.object(
            data_fetcher, "fetch_market_context_data", lambda symbol, limit=120: None
        ), patch.object(
            monitoring_module, "log_prediction", lambda *args, **kwargs: None
        ):
            result = predict_module.get_latest_prediction("BTC", df, n_iter=50)

        self.assertEqual(len(result["mean"]), 1)
        self.assertEqual(len(result["lower"]), 1)
        self.assertEqual(len(result["upper"]), 1)
        self.assertEqual(result["metadata"]["served_horizon"], 1)
        self.assertTrue(result["metadata"]["degraded_to_persistence"])
        np.testing.assert_allclose(result["mean"], np.full(1, df["close"].iloc[-1]))

    def test_frontend_has_no_three_day_forecast_copy(self):
        with open(
            os.path.join(os.getcwd(), "frontend", "src", "App.jsx"),
            encoding="utf-8",
        ) as app_file:
            app_source = app_file.read()
        with open(
            os.path.join(os.getcwd(), "frontend", "src", "components", "PriceChart.jsx"),
            encoding="utf-8",
        ) as chart_file:
            chart_source = chart_file.read()

        self.assertNotIn("3-Day Ensemble Forecast", app_source)
        self.assertNotIn("3D FORECAST", chart_source)
        self.assertNotIn("?? 3", app_source)
        self.assertNotIn("?? 3", chart_source)

    def test_evaluate_model_returns_directional_accuracy(self):
        from shared.ml.evaluate import evaluate_model
        import tensorflow as tf

        class FakeModel:
            def __call__(self, X, training=True):
                base = tf.constant([[0.55], [0.45], [0.75]], dtype=tf.float32)
                repeats = tf.shape(X)[0] // 3
                return tf.tile(base, [repeats, 1])

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

            def get_latest_version_metadata(self, coin):
                return {"version": "test-version"}

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
            lambda coin, frame, n_iter=50: {
                "mean": np.array([1.0]),
                "lower": np.array([0.9]),
                "upper": np.array([1.1]),
                "metadata": {
                    "version": "test",
                    "metrics": {
                        "directional_accuracy": 0.60,
                        "mae": 1.0,
                        "persistence_mae": 1.0,
                    },
                },
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
        self.assertGreater(len(X_train), len(X_val))
        self.assertGreater(len(X_train), len(X_test))
        self.assertGreater(len(X_val), 0)
        self.assertGreater(len(X_test), 0)
        self.assertLess(scaler.center_[0], np.median(df["close"].values))
        self.assertGreater(np.max(X_test[:, :, 0]), 1.0)

    def test_market_context_defaults_to_neutral_when_missing(self):
        from shared.utils.features import add_market_context_indicators

        index = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=index)

        result = add_market_context_indicators(df, None)

        self.assertEqual(result["funding_rate"].tolist(), [0.0, 0.0, 0.0])
        self.assertEqual(result["open_interest"].tolist(), [0.0, 0.0, 0.0])
        self.assertEqual(result["open_interest_change"].tolist(), [0.0, 0.0, 0.0])

    def test_local_artifact_store_loads_in_place_without_temp_copy(self):
        from shared.ml.storage import LocalArtifactStore
        from shared.core import config as cfg_module

        test_root = os.path.abspath("local_storage_test")
        os.makedirs(os.path.join(test_root, "BTC", "vtest"), exist_ok=True)
        artifact_path = os.path.join(test_root, "BTC", "vtest", "model.keras")
        with open(artifact_path, "w", encoding="utf-8") as handle:
            handle.write("placeholder")

        payload_path = os.path.join(test_root, "BTC", "vtest", "scaler.pkl")
        import joblib

        joblib.dump({"ok": True}, payload_path)

        with patch.object(cfg_module.settings, "LOCAL_STORAGE_DIR", test_root):
            store = LocalArtifactStore()
            self.assertEqual(os.path.normpath(store.load_model_to_path("BTC/vtest", "ignored")), os.path.normpath(artifact_path))
            self.assertEqual(store.load_joblib("BTC/vtest", "scaler.pkl", "ignored"), {"ok": True})

    def test_cached_prediction_ignores_legacy_horizon_lengths(self):
        from shared.ml.registry import ModelRegistry, CachedPrediction

        db_path = os.path.abspath("test_registry_cache.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)

        from shared.core import config as cfg_module
        with patch.object(cfg_module.settings, "USE_POSTGRES", False), patch.object(
            cfg_module.settings, "SQLITE_URL", f"sqlite:///{db_path}"
        ):
            registry = ModelRegistry()
            session = registry.Session()
            try:
                session.add(
                    CachedPrediction(
                        coin="BTC",
                        forecast={"mean": [1, 2, 3, 4, 5, 6, 7], "lower": [0] * 7, "upper": [2] * 7},
                        metadata_={"version": "legacy"},
                    )
                )
                session.commit()
            finally:
                session.close()

            self.assertIsNone(registry.get_cached_prediction("BTC"))

    def test_cached_prediction_ignores_invalid_negative_values(self):
        from shared.ml.registry import ModelRegistry, CachedPrediction

        db_path = os.path.abspath("test_registry_invalid_cache.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)

        from shared.core import config as cfg_module
        with patch.object(cfg_module.settings, "USE_POSTGRES", False), patch.object(
            cfg_module.settings, "SQLITE_URL", f"sqlite:///{db_path}"
        ):
            registry = ModelRegistry()
            session = registry.Session()
            try:
                session.add(
                    CachedPrediction(
                        coin="BTC",
                        forecast={"mean": [100.0, -1.0, 100.0], "lower": [90.0, -5.0, 90.0], "upper": [110.0, 5.0, 110.0]},
                        metadata_={"version": "bad-cache"},
                    )
                )
                session.commit()
            finally:
                session.close()

            self.assertIsNone(registry.get_cached_prediction("BTC"))

    def test_rolling_backtest_trims_extra_features_for_legacy_scalers(self):
        from shared.ml import evaluate as evaluate_module
        from shared.ml import registry as registry_module

        index = pd.date_range("2025-01-01", periods=120, freq="D")
        closes = np.linspace(100.0, 220.0, len(index))
        df = pd.DataFrame(
            {
                "open": closes - 1,
                "high": closes + 1,
                "low": closes - 2,
                "close": closes,
                "volume": np.linspace(1_000.0, 2_000.0, len(index)),
            },
            index=index,
        )

        class FakeScaler:
            n_features_in_ = 15

            def transform(self, values):
                self.last_shape = values.shape
                return values

        class FakeTargetScaler:
            def inverse_transform(self, values):
                return values

        class FakeModel:
            output_shape = (None, 3)

        class FakeRegistry:
            def load_latest_model(self, coin):
                return FakeModel(), FakeScaler(), FakeTargetScaler(), {"config": {"lookback": 20, "forecast_horizon": 3}}

            def load_latest_aux_artifact(self, coin, filename):
                return None

        with patch.object(registry_module, "get_model_registry", lambda: FakeRegistry()), patch.object(
            evaluate_module, "predict_with_uncertainty", lambda model, X_input, n_iter=50: (np.array([1.0, 1.0, 1.0]), np.array([0.9, 0.9, 0.9]), np.array([1.1, 1.1, 1.1]))
        ), patch.object(
            evaluate_module, "fetch_sentiment_data", lambda limit=200: None
        ), patch.object(
            evaluate_module, "fetch_market_context_data", lambda symbol, limit=120: None
        ):
            history = evaluate_module.execute_rolling_backtest("BTC", df, days=5)

        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_blend_predictions_uses_weighted_neural_tree_persistence(self):
        from shared.ml.predict import blend_predictions

        blended_mean, blended_lower, blended_upper = blend_predictions(
            neural_mean=np.array([110.0, 112.0, 113.0]),
            neural_lower=np.array([105.0, 107.0, 108.0]),
            neural_upper=np.array([115.0, 117.0, 118.0]),
            tree_pred=np.array([100.0, 101.0, 102.0]),
            persistence_pred=np.array([90.0, 90.0, 90.0]),
        )

        np.testing.assert_allclose(blended_mean, np.array([103.0, 104.3, 105.1]))
        np.testing.assert_allclose(blended_lower, np.array([90.0, 90.0, 90.0]))
        np.testing.assert_allclose(blended_upper, np.array([116.0, 118.6, 120.2]))

    def test_prediction_batch_skips_cache_for_bad_directional_accuracy(self):
        from shared.ml import predict as predict_module
        from shared.ml import registry as registry_module
        from shared.utils import data_fetcher

        class FakeRegistry:
            def save_cached_prediction(self, coin, forecast, metadata):
                raise AssertionError("bad directional accuracy should not be cached")

        df = pd.DataFrame(
            {
                "open": [1.0] * 80,
                "high": [1.0] * 80,
                "low": [1.0] * 80,
                "close": [1.0] * 80,
                "volume": [1.0] * 80,
            },
            index=pd.date_range("2025-01-01", periods=80, freq="D"),
        )

        with patch.object(registry_module, "get_model_registry", lambda: FakeRegistry()), patch.object(
            data_fetcher, "fetch_klines", lambda symbol, limit=5000: df
        ), patch.object(
            predict_module,
            "get_latest_prediction",
            lambda coin, frame, n_iter=50: {
                "mean": np.array([1.0, 1.0, 1.0]),
                "lower": np.array([0.9, 0.9, 0.9]),
                "upper": np.array([1.1, 1.1, 1.1]),
                "metadata": {
                    "metrics": {
                        "directional_accuracy": 0.49,
                        "eligible_for_cached_serving": False,
                    }
                },
            },
        ):
            result = predict_module.run_prediction_batch(coins=["BTC"], n_iter=50)

        self.assertIn("directional_accuracy=0.49", result["BTC"])

    def test_training_cache_eligibility_rejects_mae_far_worse_than_persistence(self):
        from shared.ml.training import _is_eligible_for_cached_serving

        self.assertFalse(
            _is_eligible_for_cached_serving(
                {
                    "directional_accuracy": 0.83,
                    "mae": 7_000_000.0,
                    "persistence_mae": 3_000.0,
                }
            )
        )

    def test_prediction_batch_skips_mock_data_for_cached_serving(self):
        from shared.ml import predict as predict_module
        from shared.ml import registry as registry_module
        from shared.utils import data_fetcher

        class FakeRegistry:
            def save_cached_prediction(self, coin, forecast, metadata):
                raise AssertionError("mock data should not be cached")

        df = pd.DataFrame(
            {
                "open": [1.0] * 80,
                "high": [1.0] * 80,
                "low": [1.0] * 80,
                "close": [1.0] * 80,
                "volume": [1.0] * 80,
                "source": ["Mock"] * 80,
            },
            index=pd.date_range("2025-01-01", periods=80, freq="D"),
        )

        with patch.object(registry_module, "get_model_registry", lambda: FakeRegistry()), patch.object(
            data_fetcher, "fetch_klines", lambda symbol, limit=5000: df
        ):
            result = predict_module.run_prediction_batch(coins=["BTC"], n_iter=50)

        self.assertEqual(result["BTC"], "skipped: mock data unavailable for cached serving")

    def test_live_predict_refuses_mock_data(self):
        from fastapi import HTTPException
        from services.api.routes import endpoints
        from shared.ml import cache as cache_module
        from shared.ml import registry as registry_module
        from shared.utils import data_fetcher

        class FakeRegistry:
            def get_cached_prediction(self, coin):
                return None

        class FakeCache:
            def get(self, key):
                return None

            def delete(self, key):
                return None

        df = pd.DataFrame(
            {
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "volume": [1.0],
                "source": ["Mock"],
            },
            index=pd.date_range("2025-01-01", periods=1, freq="D"),
        )

        with patch.object(cache_module, "cache", FakeCache()), patch.object(
            registry_module, "get_model_registry", lambda: FakeRegistry()
        ), patch.object(data_fetcher, "fetch_klines", lambda symbol, limit=5000: df):
            with self.assertRaises(HTTPException) as ctx:
                endpoints.predict_coin("BTC")

        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
