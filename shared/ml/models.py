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

UPGRADE: Added Bahdanau-style attention after the LSTM branch in both models.
        LSTM now returns all timestep hidden states (return_sequences=True).
        Attention scores each timestep, builds a weighted context vector, and
        passes it to the Dense head. This lets the model focus on the candles
        that actually preceded big moves rather than treating all timesteps
        equally. The flat Concatenate on the LSTM output is replaced by this
        context vector — CNN branch and Dense head are unchanged.

Both use Dropout(training=True) in every Dropout layer to support Monte
Carlo Dropout inference: calling model(X, training=True) gives a stochastic
sample; running n_iter such calls and averaging gives mean + uncertainty.
"""
import tensorflow as tf
import keras
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, LSTM, Dense, Dropout,
    Conv1D, MaxPooling1D, Flatten, Concatenate,
    Layer,
)
from tensorflow.keras.optimizers import Adam


@keras.saving.register_keras_serializable(package="CryptoQuant")
class BahdanauAttention(Layer):
    """
    Bahdanau-style additive attention over LSTM hidden states.

    Takes the full sequence of LSTM hidden states (batch, timesteps, units)
    and returns a single context vector (batch, units) — a weighted sum of
    all timestep states where the weights are learned during training.

    The model learns to assign high weight to timesteps that are most
    predictive of the next price move (e.g. a volatility spike, a support
    break) and low weight to quiet consolidation candles.

    Compatible with MC Dropout: no internal state, no normalization layers,
    fully deterministic given weights — stochasticity comes from Dropout
    layers wrapping this in the parent model.
    """

    def __init__(self, units: int = 64, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        # W1 projects each hidden state into attention space
        self.W1 = Dense(units, use_bias=False, name=f"{self.name}_W1")
        # v scores the projected state down to a scalar
        self.v  = Dense(1,     use_bias=False, name=f"{self.name}_v")

    def call(self, hidden_states):
        """
        Args:
            hidden_states: (batch, timesteps, lstm_units)

        Returns:
            context: (batch, lstm_units) — weighted sum across timesteps
            weights: (batch, timesteps)  — attention weights (sum to 1)
        """
        # Score each timestep: (batch, timesteps, units) -> (batch, timesteps, 1)
        score = self.v(tf.nn.tanh(self.W1(hidden_states)))

        # Softmax across timestep axis to get weights that sum to 1
        weights = tf.nn.softmax(score, axis=1)          # (batch, timesteps, 1)

        # Weighted sum across timesteps
        context = tf.reduce_sum(weights * hidden_states, axis=1)  # (batch, lstm_units)

        return context, weights

    def get_config(self):
        config = super().get_config()
        config.update({"units": self.units})
        return config


def build_model(input_shape, output_steps: int = 7, dropout_rate: float = 0.2) -> Model:
    """
    Parallel LSTM + CNN with Bahdanau Attention and MC Dropout.

    Changes from previous version:
    - LSTM now uses return_sequences=True to expose all timestep hidden states
    - BahdanauAttention layer scores each timestep and returns a context vector
    - Context vector replaces the flat LSTM output fed into Concatenate
    - CNN branch and Dense head are identical to before

    Everything else (MC Dropout, MSE loss, Adam lr, no BatchNorm) unchanged.

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
    # return_sequences=True so attention can see all timestep hidden states
    l = LSTM(128, return_sequences=True, name="lstm_1")(inputs)
    l = Dropout(dropout_rate, name="lstm_drop")(l, training=True)

    # Attention: score each timestep, return weighted context vector
    l, _ = BahdanauAttention(units=64, name="attention")(l)
    # l is now (batch, 128) — same shape as before, just smarter aggregation

    # --- CNN Branch: captures local volatility/spikes (unchanged) ---
    c = Conv1D(filters=64, kernel_size=3, padding="same", name="conv_1")(inputs)
    c = LeakyReLU(alpha=0.1, name="conv_act_1")(c)
    c = Conv1D(filters=32, kernel_size=3, padding="same", name="conv_2")(c)
    c = LeakyReLU(alpha=0.1, name="conv_act_2")(c)
    c = MaxPooling1D(pool_size=2, name="pool_1")(c)
    c = Flatten(name="flatten")(c)
    c = Dropout(dropout_rate, name="cnn_drop")(c, training=True)

    # --- Merge & Head (unchanged) ---
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
    Hybrid LSTM + 1D-CNN ensemble with Bahdanau Attention and MC Dropout.

    Changes from previous version:
    - Second LSTM now uses return_sequences=True to expose all hidden states
    - BahdanauAttention layer added after second LSTM dropout
    - Context vector replaces flat LSTM output fed into Concatenate
    - CNN branch, Dense head, and dual-dropout structure unchanged

    Args:
        input_shape   : (lookback, n_features)
        output_steps  : forecast horizon (days)
        dropout_rate  : MC Dropout rate

    Returns:
        Compiled Keras Model
    """
    inputs = Input(shape=input_shape, name="price_sequence")

    # ── LSTM branch ──────────────────────────────────────────────────────────
    # First LSTM compresses sequence — return_sequences=True feeds into second
    lstm = LSTM(64, return_sequences=True, name="lstm_1")(inputs)
    lstm = Dropout(dropout_rate, name="lstm_drop_1")(lstm, training=True)
    # Second LSTM: return_sequences=True so attention can see all hidden states
    lstm = LSTM(32, return_sequences=True, name="lstm_2")(lstm)
    lstm = Dropout(dropout_rate, name="lstm_drop_2")(lstm, training=True)

    # Attention: score each timestep, return weighted context vector
    lstm, _ = BahdanauAttention(units=32, name="attention")(lstm)
    # lstm is now (batch, 32) — same shape as before

    # ── CNN branch (unchanged) ───────────────────────────────────────────────
    cnn = Conv1D(filters=64, kernel_size=3, activation="relu",
                 padding="same", name="conv_1")(inputs)
    cnn = MaxPooling1D(pool_size=2, name="pool_1")(cnn)
    cnn = Conv1D(filters=32, kernel_size=3, activation="relu",
                 padding="same", name="conv_2")(cnn)
    cnn = Flatten(name="flatten")(cnn)
    cnn = Dropout(dropout_rate, name="cnn_drop")(cnn, training=True)

    # ── Merge (unchanged) ────────────────────────────────────────────────────
    merged = Concatenate(name="merge")([lstm, cnn])

    x = Dense(64, activation="relu", name="dense_1")(merged)
    x = Dropout(dropout_rate, name="dense_drop")(x, training=True)

    outputs = Dense(output_steps, name="forecast")(x)

    model = Model(inputs=inputs, outputs=outputs, name="CryptoHybrid")
    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model