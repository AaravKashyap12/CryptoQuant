"""
Tests for ModelRegistry.

Uses a tmp-path SQLite database and local filesystem storage so tests run
in complete isolation without any network calls.
"""
import pytest
import os
import numpy as np
from sklearn.preprocessing import MinMaxScaler


# ── Helpers ──────────────────────────────────────────────────────────────────

def create_dummy_model(lookback: int = 10, n_features: int = 5, output_steps: int = 7):
    """
    Minimal Keras model that matches the real LSTM input/output signature:
      input  → (batch, lookback, n_features)
      output → (batch, output_steps)
    """
    import tensorflow as tf
    from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
    from tensorflow.keras.models import Model

    inputs  = Input(shape=(lookback, n_features))
    x       = LSTM(16, return_sequences=False)(inputs)
    x       = Dropout(0.2)(x, training=True)
    outputs = Dense(output_steps)(x)
    model   = Model(inputs, outputs)
    model.compile(optimizer="adam", loss="mse")
    return model


def make_scalers():
    scaler        = MinMaxScaler(); scaler.fit(np.random.rand(20, 5))
    target_scaler = MinMaxScaler(); target_scaler.fit(np.random.rand(20, 1))
    return scaler, target_scaler


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def registry(tmp_path, monkeypatch):
    """
    Isolated ModelRegistry using:
      - tmp SQLite database (avoids collisions between test runs)
      - local filesystem storage (no S3 calls)
      - Redis disabled (uses in-process cache)
    """
    # Monkeypatch settings BEFORE importing ModelRegistry so the singleton
    # picks up the overridden values. Pydantic v2 Settings are immutable, so
    # we cannot assign to them directly — monkeypatch replaces them on the object.
    from shared.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "SQLITE_URL",        f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(cfg_module.settings, "LOCAL_STORAGE_DIR", str(tmp_path / "models"))
    monkeypatch.setattr(cfg_module.settings, "USE_S3",            False)
    monkeypatch.setattr(cfg_module.settings, "USE_POSTGRES",      False)
    monkeypatch.setattr(cfg_module.settings, "USE_REDIS",         False)



    from shared.ml.storage import LocalArtifactStore
    import shared.ml.storage as stor
    monkeypatch.setattr(stor, "get_artifact_store", lambda: LocalArtifactStore())

    # Import fresh registry (don't use the global singleton)
    from shared.ml.registry import ModelRegistry
    reg = ModelRegistry()
    yield reg
    reg.dispose()


# ── Tests ────────────────────────────────────────────────────────────────────

def test_save_and_load_model(registry):
    """Basic round-trip: save a model, reload it, verify metadata."""
    coin             = "BTC-TEST"
    model            = create_dummy_model()
    scaler, t_scaler = make_scalers()

    version = registry.save_model(coin, model, scaler, t_scaler, metrics={"mae": 0.01})
    assert version.startswith("v"), f"Expected version string, got: {version}"

    loaded_model, l_scaler, l_target, meta = registry.load_latest_model(coin)
    assert loaded_model is not None
    assert meta["version"]          == version
    assert meta["config"]["lookback"]  == 10   # dummy model input_shape[1]
    assert meta["config"]["features"]  == 5    # dummy model input_shape[2]


def test_cache_holds_all_five_coins(registry):
    """
    Registry should keep all 5 coins in memory simultaneously.
    Before the fix it evicted at 1 (and called K.clear_session), breaking
    all other loaded models.
    """
    scaler, t_scaler = make_scalers()
    coins = ["BTC-T", "ETH-T", "BNB-T", "SOL-T", "ADA-T"]

    for coin in coins:
        registry.save_model(coin, create_dummy_model(), scaler, t_scaler)

    for coin in coins:
        m, _, _, meta = registry.load_latest_model(coin)
        assert m is not None, f"Model for {coin} should still be cached"

    assert len(registry._model_cache) == 5, "All 5 models should live in cache simultaneously"


def test_cache_lru_evicts_oldest_when_over_limit(registry):
    """
    When a 6th coin is loaded, the oldest entry is evicted — not all of them.
    No K.clear_session() is called, so the remaining 5 are untouched.
    """
    scaler, t_scaler = make_scalers()
    coins = ["C1", "C2", "C3", "C4", "C5", "C6"]   # 6 > MAX_COINS=5

    for coin in coins:
        registry.save_model(coin, create_dummy_model(), scaler, t_scaler)

    for coin in coins:
        registry.load_latest_model(coin)

    assert len(registry._model_cache) == 5
    assert "C1_v1.0.0" not in registry._model_cache, "Oldest entry should have been evicted"
    assert "C6_v1.0.0" in registry._model_cache,     "Newest entry should be in cache"


def test_cached_prediction_store(registry):
    """Verify upsert and retrieval of precomputed predictions."""
    coin     = "BTC-PRED"
    forecast = {"mean": [100.0, 101.0], "lower": [98.0, 99.0], "upper": [102.0, 103.0]}
    metadata = {"version": "v1.0.0", "config": {"lookback": 60}}

    registry.save_cached_prediction(coin, forecast, metadata)
    result = registry.get_cached_prediction(coin)

    assert result is not None
    assert result["forecast"]["mean"] == forecast["mean"]


def test_cached_prediction_upsert(registry):
    """Second save should update, not duplicate."""
    coin      = "ETH-PRED"
    forecast1 = {"mean": [200.0], "lower": [195.0], "upper": [205.0]}
    forecast2 = {"mean": [210.0], "lower": [205.0], "upper": [215.0]}
    meta      = {"version": "v1.0.0", "config": {}}

    registry.save_cached_prediction(coin, forecast1, meta)
    registry.save_cached_prediction(coin, forecast2, meta)

    result = registry.get_cached_prediction(coin)
    assert result["forecast"]["mean"] == forecast2["mean"], "Should return the latest prediction"


def test_version_increment(registry):
    """Each save for the same coin should bump the patch version."""
    scaler, t_scaler = make_scalers()
    coin = "ETH-VER"

    v1 = registry.save_model(coin, create_dummy_model(), scaler, t_scaler)
    v2 = registry.save_model(coin, create_dummy_model(), scaler, t_scaler)

    assert v1 == "v1.0.0"
    assert v2 == "v1.0.1"


def test_load_nonexistent_coin(registry):
    """Loading a coin with no registered model should return all None."""
    m, s, ts, meta = registry.load_latest_model("NONEXISTENT")
    assert m    is None
    assert s    is None
    assert ts   is None
    assert meta is None