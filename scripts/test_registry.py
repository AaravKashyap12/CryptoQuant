import os
import sys
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from sklearn.preprocessing import MinMaxScaler

# Add project root to path
sys.path.append(os.getcwd())

from shared.ml.registry import ModelRegistry

def create_dummy_model():
    model = Sequential([
        Input(shape=(10, 5)),
        Dense(10, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def test_registry():
    print("Initializing Registry...")
    registry = ModelRegistry()
    
    coin = "TEST_COIN"
    
    # 1. Create Artifacts
    print("Creating dummy artifacts...")
    model = create_dummy_model()
    scaler = MinMaxScaler()
    scaler.fit(np.random.rand(100, 5))
    target_scaler = MinMaxScaler()
    target_scaler.fit(np.random.rand(100, 1))
    
    metrics = {"mse": 0.01, "mae": 0.05}
    
    # 2. Save
    print("Saving model to registry...")
    try:
        version = registry.save_model(coin, model, scaler, target_scaler, metrics)
        print(f"Success! Version: {version}")
    except Exception as e:
        print(f"Save failed: {e}")
        return

    # 3. Load
    print(f"Loading model {version}...")
    try:
        loaded_model, l_scaler, l_target, meta = registry.load_latest_model(coin)
        
        if loaded_model is None:
            print("Failed to load model (None returned)")
            return
            
        print(f"Loaded Meta: {meta}")
        
        # Verify
        assert meta['version'] == version
        assert meta['metrics']['mse'] == 0.01
        print("Verification Successful!")
        
    except Exception as e:
        print(f"Load failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registry()
