import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor


def assert_no_sequence_target_overlap(sample_end: int, lookback: int, horizon: int) -> None:
    input_window = range(sample_end - lookback, sample_end)
    target_window = range(sample_end, sample_end + horizon)
    if not set(input_window).isdisjoint(target_window):
        raise ValueError("Input window overlaps target window; tabular features would leak target data.")


def sequence_to_tabular_features(X: np.ndarray) -> np.ndarray:
    """
    Reduce a lookback window to a tabular feature vector.

    For this repo the last timestep already contains engineered moving-window
    indicators, so using the most recent row gives the tree model a clean,
    low-variance tabular input.
    """
    return X[:, -1, :]


def build_tabular_model(random_state: int = 42):
    base = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_depth=4,
        max_iter=300,
        min_samples_leaf=8,
        l2_regularization=1e-3,
        random_state=random_state,
    )
    return MultiOutputRegressor(base)


def train_tabular_model(X_train: np.ndarray, y_train: np.ndarray):
    model = build_tabular_model()
    model.fit(sequence_to_tabular_features(X_train), y_train)
    return model


def predict_tabular_model(model, X: np.ndarray) -> np.ndarray:
    return np.asarray(model.predict(sequence_to_tabular_features(X)))
