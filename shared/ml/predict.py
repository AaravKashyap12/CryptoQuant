import numpy as np
import tensorflow as tf
from shared.ml.registry import ModelRegistry
from shared.utils.preprocess import prepare_inference_data

def predict_with_uncertainty(model, X, n_iter=20):
    """
    Run Monte Carlo Dropout using vectorized batching.
    """
    # Repeat X into a batch of size n_iter
    # X shape: (1, lookback, features) -> (n_iter, lookback, features)
    X_batch = np.repeat(X, n_iter, axis=0)
    
    # Run all predictions in one parallel batch
    # Shape: (n_iter, output_steps)
    predictions = model(X_batch, training=True).numpy()
    
    mean_pred = np.mean(predictions, axis=0)
    lower_bound = np.percentile(predictions, 5, axis=0)
    upper_bound = np.percentile(predictions, 95, axis=0)
    
    return mean_pred, lower_bound, upper_bound

def get_latest_prediction(coin, df, n_iter=20):
    """
    Loads latest model, prepares data, and runs prediction.
    """
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)
    
    if model is None:
        print(f"No model found for {coin}")
        return None
        
    lookback = metadata['config']['lookback']
    version = metadata.get('version', 'unknown')
    
    # Prepare Input
    import time
    from shared.ml.monitoring import log_prediction
    
    start_time = time.time()
    X_input = prepare_inference_data(df, scaler, lookback=lookback)
    
    # Run Inference
    mean_scaled, lower_scaled, upper_scaled = predict_with_uncertainty(model, X_input, n_iter=n_iter)
    
    # Inverse Transform
    # target_scaler was fitted on (n_samples, 1). We have (output_steps,)
    # Reshape to (-1, 1) for inverse_transform
    mean_price = target_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).flatten()
    lower_price = target_scaler.inverse_transform(lower_scaled.reshape(-1, 1)).flatten()
    upper_price = target_scaler.inverse_transform(upper_scaled.reshape(-1, 1)).flatten()
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Log for Monitoring
    version = metadata.get('version', 'unknown')
    log_prediction(coin, version, X_input, mean_scaled, latency_ms)
    
    return {
        "mean": mean_price,
        "lower": lower_price,
        "upper": upper_price,
        "metadata": metadata
    }
