import os
import sys
sys.path.append(os.getcwd())
from shared.ml.registry import get_model_registry

registry = get_model_registry()
for coin in ['BTC', 'ETH', 'BNB', 'SOL', 'ADA']:
    v = registry.get_latest_version(coin)
    meta = registry.get_latest_version_metadata(coin)
    if meta:
        metrics = meta.get('metrics', {})
        print(f"{coin}: {v} | MAE: {metrics.get('mae', 'N/A')} | Source: {meta.get('source', 'unknown')}")
        print(f"      Trained: {metrics.get('trained_at')}")
    else:
        print(f"{coin}: No model found")
