import os
import json
import joblib
from datetime import datetime

MODELS_DIR = "models"

# Global cache to persist across requests
_MODEL_CACHE = {}

class ModelRegistry:
    def __init__(self, base_dir=MODELS_DIR):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
    def get_latest_version(self, coin):
        """Finds the latest version for a specific coin."""
        coin_dir = os.path.join(self.base_dir, coin)
        if not os.path.exists(coin_dir):
            return "v0.0.0"
            
        versions = [d for d in os.listdir(coin_dir) if d.startswith("v")]
        if not versions:
            return "v0.0.0"
            
        # simple sort by string
        versions.sort() 
        return versions[-1]
        
    def _increment_version(self, version):
        """Simple patch increment."""
        major, minor, patch = map(int, version[1:].split('.'))
        return f"v{major}.{minor}.{patch+1}"
        
    def save_model(self, coin, model, scaler, target_scaler, metrics=None):
        """
        Saves model, scalers, and metadata to a new version directory.
        """
        latest = self.get_latest_version(coin)
        new_version = self._increment_version(latest)
        
        save_dir = os.path.join(self.base_dir, coin, new_version)
        os.makedirs(save_dir)
        
        # Save Keras Model
        model_path = os.path.join(save_dir, "model.keras")
        model.save(model_path)
        
        # Save Scalers
        joblib.dump(scaler, os.path.join(save_dir, "scaler.pkl"))
        joblib.dump(target_scaler, os.path.join(save_dir, "target_scaler.pkl"))
        
        # Save Metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "version": new_version,
            "metrics": metrics or {},
            "config": {
                "lookback": model.input_shape[1],
                "features": model.input_shape[2]
            }
        }
        with open(os.path.join(save_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        print(f"Saved {coin} model version {new_version} to {save_dir}")
        return new_version

    def load_latest_model(self, coin):
        """Loads the latest model and scalers for a coin (with caching)."""
        latest = self.get_latest_version(coin)
        if latest == "v0.0.0":
            return None, None, None, None
            
        # Check Cache
        cache_key = f"{coin}_{latest}"
        if cache_key in _MODEL_CACHE:
            print(f"Loading {coin} model from CACHE (cached)")
            return _MODEL_CACHE[cache_key]
            
        load_dir = os.path.join(self.base_dir, coin, latest)
        
        try:
            from tensorflow.keras.models import load_model
            
            print(f"Loading {coin} model from DISK")
            
            # Load Model
            model = load_model(os.path.join(load_dir, "model.keras"))
            
            # Load Scalers
            scaler = joblib.load(os.path.join(load_dir, "scaler.pkl"))
            target_scaler = joblib.load(os.path.join(load_dir, "target_scaler.pkl"))
            
            # Load Metadata
            with open(os.path.join(load_dir, "metadata.json"), "r") as f:
                metadata = json.load(f)
                
            # Store in Cache
            _MODEL_CACHE[cache_key] = (model, scaler, target_scaler, metadata)
                
            return model, scaler, target_scaler, metadata
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to load {coin} {latest}: {e}")
            return None, None, None, None
