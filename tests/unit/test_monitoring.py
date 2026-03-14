import pytest
import numpy as np
import pandas as pd
from shared.ml.monitoring import calculate_psi, detect_drift

def test_calculate_psi():
    # Identical distributions should have PSI ~ 0
    expected = np.random.normal(0, 1, 1000)
    actual = np.random.normal(0, 1, 1000)
    psi = calculate_psi(expected, actual)
    assert psi < 0.1
    
    # Drifted distributions should have high PSI
    drifted = np.random.normal(2, 1, 1000)
    psi_drift = calculate_psi(expected, drifted)
    assert psi_drift > 0.1

def test_detect_drift():
    train_df = pd.DataFrame({
        "feat1": np.random.normal(0, 1, 1000),
        "feat2": np.random.uniform(0, 10, 1000)
    })
    
    # No drift
    serving_df_ok = pd.DataFrame({
        "feat1": np.random.normal(0, 1, 1000),
        "feat2": np.random.uniform(0, 10, 1000)
    })
    
    report_ok = detect_drift(train_df, serving_df_ok)
    assert report_ok["drift_detected"] == False
    
    # With drift
    serving_df_drift = pd.DataFrame({
        "feat1": np.random.normal(5, 1, 1000), # Mean shifted 0 -> 5
        "feat2": np.random.uniform(0, 10, 1000)
    })
    
    report_drift = detect_drift(train_df, serving_df_drift)
    assert report_drift["drift_detected"] == True
    assert report_drift["features"]["feat1"] > 0.1
