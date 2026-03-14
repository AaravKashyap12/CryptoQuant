"""
Neural network architectures for CryptoQuant.

build_model        — Parallel LSTM + CNN with MC Dropout on both branches.
build_hybrid_model — Full hybrid ensemble (same architecture, more capacity).

FIX 1: build_model previously fed input through CNN first then into LSTM
        (sequential). This meant LSTM never saw raw price sequences — only a
        compressed, pooled representation. Fixed to run LSTM and CNN in
        parallel (same as build_hybrid_model) so each branch sees the full
        raw sequence.

FIX 2: CNN branch in build_hybrid_model had no Dropout layer, making half
        the model deterministic during MC Dropout inference. Uncertainty
        bands were underestimated. Added Dropout after Flatten on CNN branch
        in both models.

Both use Dropout(training=True) in every Dropout layer to support Monte
Carlo Dropout inference: calling model(X, training=True) gives a stochastic
sample; running n_iter such calls and averaging gives mean + uncertainty.
"""
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, LSTM, Dense, Dropout,
    Conv1D, MaxPooling1D, Flatten, Concatenate,
)
from tensorflow.keras.optimizers import Adam


def build_model(input_shape, output_steps: int = 7, dropout_rate: float = 0.2) -> Model:
    """
    Parallel LSTM + CNN with MC Dropout.

    Upgrades over original (conservative — no normalization layers):
    - LSTM: 128 units (up from 64) for richer temporal representations
    - CNN: Two Conv1D layers (64 + 32 filters) for deeper local patterns
    - Deeper Dense head (64 → 32 → forecast) with LeakyReLU
    - MSE loss (proven stable for MinMax-scaled time series)

    NOTE: No BatchNormalization or LayerNormalization — normalization layers
    interact badly with MC Dropout (training=True changes their behaviour).

    Args:
        input_shape   : (lookback, n_features)
        output_steps  : forecast horizon (days)
        dropout_rate  : applied after both branches; training=True keeps it
                        active during inference for uncertainty estimation

    Returns:
        Compiled Keras Model
    """
    from tensorflow.keras.layers import LeakyReLU

    inputs = Input(shape=input_shape, name="price_sequence")

    # --- LSTM Branch: captures long-range trend ---
    l = LSTM(128, return_sequences=False, name="lstm_1")(inputs)
    l = Dropout(dropout_rate, name="lstm_drop")(l, training=True)

    # --- CNN Branch: captures local volatility/spikes ---
    c = Conv1D(filters=64, kernel_size=3, padding="same", name="conv_1")(inputs)
    c = LeakyReLU(alpha=0.1, name="conv_act_1")(c)
    c = Conv1D(filters=32, kernel_size=3, padding="same", name="conv_2")(c)
    c = LeakyReLU(alpha=0.1, name="conv_act_2")(c)
    c = MaxPooling1D(pool_size=2, name="pool_1")(c)
    c = Flatten(name="flatten")(c)
    c = Dropout(dropout_rate, name="cnn_drop")(c, training=True)

    # --- Merge & Head ---
    merged = Concatenate(name="merge")([l, c])
    x = Dense(64, name="dense_1")(merged)
    x = LeakyReLU(alpha=0.1, name="dense_act_1")(x)
    x = Dense(32, name="dense_2")(x)
    x = LeakyReLU(alpha=0.1, name="dense_act_2")(x)
    outputs = Dense(output_steps, name="forecast")(x)

    model = Model(inputs=inputs, outputs=outputs, name="CryptoDynamic")
    model.compile(optimizer=Adam(learning_rate=0.0008), loss="mse", metrics=["mae"])
    return model


def build_hybrid_model(input_shape, output_steps: int = 7, dropout_rate: float = 0.2) -> Model:
    """
    Hybrid LSTM + 1D-CNN ensemble with MC Dropout on both branches.

    FIXED: Added Dropout after CNN Flatten so both branches contribute to
    uncertainty estimation during MC Dropout inference. Previously only the
    LSTM branch was stochastic, causing confidence bands to be too narrow.

    Args:
        input_shape   : (lookback, n_features)
        output_steps  : forecast horizon (days)
        dropout_rate  : MC Dropout rate

    Returns:
        Compiled Keras Model
    """
    inputs = Input(shape=input_shape, name="price_sequence")

    # ── LSTM branch ──────────────────────────────────────────────────────────
    lstm = LSTM(64, return_sequences=True, name="lstm_1")(inputs)
    lstm = Dropout(dropout_rate, name="lstm_drop_1")(lstm, training=True)
    lstm = LSTM(32, return_sequences=False, name="lstm_2")(lstm)
    # Second dropout on LSTM output for deeper stochasticity
    lstm = Dropout(dropout_rate, name="lstm_drop_2")(lstm, training=True)

    # ── CNN branch ───────────────────────────────────────────────────────────
    cnn = Conv1D(filters=64, kernel_size=3, activation="relu",
                 padding="same", name="conv_1")(inputs)
    cnn = MaxPooling1D(pool_size=2, name="pool_1")(cnn)
    cnn = Conv1D(filters=32, kernel_size=3, activation="relu",
                 padding="same", name="conv_2")(cnn)
    cnn = Flatten(name="flatten")(cnn)
    # FIXED: Dropout on CNN branch so MC passes are stochastic here too
    cnn = Dropout(dropout_rate, name="cnn_drop")(cnn, training=True)

    # ── Merge ────────────────────────────────────────────────────────────────
    merged = Concatenate(name="merge")([lstm, cnn])

    x = Dense(64, activation="relu", name="dense_1")(merged)
    x = Dropout(dropout_rate, name="dense_drop")(x, training=True)

    outputs = Dense(output_steps, name="forecast")(x)

    model = Model(inputs=inputs, outputs=outputs, name="CryptoHybrid")
    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model