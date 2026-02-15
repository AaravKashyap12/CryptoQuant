import pytest
import os
import shutil
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from sklearn.preprocessing import MinMaxScaler
from shared.ml.registry import ModelRegistry
from shared.core.config import settings

@pytest.fixture
def registry(tmp_path):
    # Create a temp database path
    db_path = tmp_path / "test_registry.db"
    storage_dir = tmp_path / "models_storage"
    
    # Override settings for the test
    settings.SQLITE_URL = f"sqlite:///{db_path}"
    settings.LOCAL_STORAGE_DIR = str(storage_dir)
    settings.USE_S3 = False
    settings.USE_POSTGRES = False
    
    reg = ModelRegistry()
    yield reg
    
    # Cleanup: dispose engine to release file lock
    reg.dispose()
    # tmp_path is automatically cleaned up by pytest

def create_dummy_model():
    model = Sequential([
        Input(shape=(10, 5)),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def test_save_load_model(registry):
    coin = "BTC-TEST"
    model = create_dummy_model()
    scaler = MinMaxScaler()
    scaler.fit(np.random.rand(10, 5))
    target_scaler = MinMaxScaler()
    target_scaler.fit(np.random.rand(10, 1))
    
    # Save
    version = registry.save_model(coin, model, scaler, target_scaler)
    assert version.startswith("v")
    
    # Load
    loaded_model, l_scaler, l_target, meta = registry.load_latest_model(coin)
    assert loaded_model is not None
    assert meta['version'] == version
    assert meta['config']['lookback'] == 10
