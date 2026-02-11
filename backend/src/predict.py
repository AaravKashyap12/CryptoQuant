import numpy as np
import tensorflow as tf
from src.registry import ModelRegistry
from src.preprocess import prepare_inference_data

def predict_with_uncertainty(model, X, n_iter=20):
    """
    Run Monte Carlo Dropout to get prediction distribution.
    
    Args:
        model: Trained Keras model (with Dropout layers).
        X: Input data (1, lookback, n_features).
        n_iter: Number of stochastic forward passes.
        
    Returns:
        mean_pred: Average prediction [1, output_steps]
        lower_bound: 5th percentile
        upper_bound: 95th percentile
    """
    # Force dropout during inference by setting training=True
    # We need to use valid Keras functional API call or custom loop
    # Simple way: model(X, training=True)
    
    predictions = []
    for _ in range(n_iter):
        # Shape: (1, output_steps)
        pred = model(X, training=True) 
        predictions.append(pred.numpy())
        
    predictions = np.array(predictions) # (n_iter, 1, output_steps)
    
    # Squeeze to (n_iter, output_steps)
    predictions = predictions.squeeze(axis=1)
    
    mean_pred = np.mean(predictions, axis=0)
    lower_bound = np.percentile(predictions, 5, axis=0)
    upper_bound = np.percentile(predictions, 95, axis=0)
    
    return mean_pred, lower_bound, upper_bound

def get_latest_prediction(coin, df, n_iter=20):
    """
    Loads latest model, prepares data, and runs prediction.
    
    Args:
        coin (str): Symbol e.g. "BTCUSDT"
        df (pd.DataFrame): Recent OHLCV data
        n_iter (int): MC Dropout iterations
        
    Returns:
        dict with:
            'mean': np.array (7 days),
            'lower': np.array,
            'upper': np.array,
            'dates': list of datetime,
            'metadata': dict
    """
    registry = ModelRegistry()
    model, scaler, target_scaler, metadata = registry.load_latest_model(coin)
    
    if model is None:
        print(f"No model found for {coin}")
        return None
        
    lookback = metadata['config']['lookback']
    
    # Prepare Input
    # This handles scaling internally
    X_input = prepare_inference_data(df, scaler, lookback=lookback)
    
    # Run Inference
    mean_scaled, lower_scaled, upper_scaled = predict_with_uncertainty(model, X_input, n_iter=n_iter)
    
    # Inverse Transform
    # target_scaler was fitted on (n_samples, 1). We have (output_steps,)
    # Reshape to (-1, 1) for inverse_transform
    mean_price = target_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).flatten()
    lower_price = target_scaler.inverse_transform(lower_scaled.reshape(-1, 1)).flatten()
    upper_price = target_scaler.inverse_transform(upper_scaled.reshape(-1, 1)).flatten()
    
    return {
        "mean": mean_price,
        "lower": lower_price,
        "upper": upper_price,
        "metadata": metadata
    }
