import numpy as np
import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger("MLMonitoring")

def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """
    Calculate the Population Stability Index (PSI) between two distributions.
    Ref: https://www.listendata.com/2015/05/population-stability-index.html
    """
    def scale_range(data, min_val, max_val):
        return (data - min_val) / (max_val - min_val)

    # Combine to find global range for binning
    min_v = min(expected.min(), actual.min())
    max_v = max(expected.max(), actual.max())
    
    # Avoid division by zero if all values are same
    if max_v == min_v:
        return 0.0

    # Create bins
    bins = np.linspace(min_v, max_v, buckets + 1)
    
    expected_percents = np.histogram(expected, bins=bins)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=bins)[0] / len(actual)

    # Avoid zero percentages (clip to small epsilon)
    expected_percents = np.clip(expected_percents, a_min=1e-6, a_max=None)
    actual_percents = np.clip(actual_percents, a_min=1e-6, a_max=None)

    psi_value = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
    return float(psi_value)

def detect_drift(training_data: pd.DataFrame, serving_data: pd.DataFrame, threshold: float = 0.1) -> Dict[str, Any]:
    """
    Compares training features vs serving features to detect drift.
    Returns: Dict with PSI values per feature and alert flag.
    """
    drift_report = {"drift_detected": False, "features": {}}
    
    # Common features
    common_cols = list(set(training_data.columns) & set(serving_data.columns))
    
    for col in common_cols:
        psi = calculate_psi(training_data[col].values, serving_data[col].values)
        drift_report["features"][col] = psi
        if psi > threshold:
            drift_report["drift_detected"] = True
            logger.warning(f"Feature Drift Detected: {col} (PSI: {psi:.4f} > {threshold})")
            
    return drift_report

def log_prediction(coin: str, version: str, inputs: np.ndarray, outputs: np.ndarray, latency_ms: float):
    """
    Entry point for logging serving data. 
    In production, this would save to a table or a stream (e.g., Kafka/Kinesis).
    For now, we log to a file or standard logger.
    """
    # Summary of stats
    input_mean = np.mean(inputs)
    output_mean = np.mean(outputs)
    
    logger.info(f"PREDICTION LOG | {coin} | {version} | Latency: {latency_ms:.2f}ms | InMean: {input_mean:.4f} | OutMean: {output_mean:.4f}")
    
    # TODO: Save to a persistent store for drift analysis later
