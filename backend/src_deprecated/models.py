import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam

class CryptoLSTM(Model):
    def __init__(self, input_shape, output_steps=7, dropout_rate=0.2):
        super(CryptoLSTM, self).__init__()
        self.input_shape_val = input_shape
        self.output_steps = output_steps
        self.dropout_rate = dropout_rate
        
        # Layers
        # We use Functional API style internally or Subclassing? 
        # Subclassing is harder to serialize sometimes. Let's use Functional API 
        # inside a build method or just return a compiled model.
        pass

def build_model(input_shape, output_steps=7, dropout_rate=0.2):
    """
    Builds and compiles the LSTM model with support for MC Dropout.
    
    Args:
        input_shape (tuple): (lookback, n_features)
        output_steps (int): Number of days to predict (e.g., 7)
        dropout_rate (float): Dropout rate (0.0 to 1.0)
        
    Returns:
        model (tf.keras.Model): Compiled model
    """
    inputs = Input(shape=input_shape)
    
    # LSTM Layers
    # return_sequences=True for stacking
    x = LSTM(64, return_sequences=True)(inputs)
    x = Dropout(dropout_rate)(x, training=True) # training=True enables MC Dropout
    
    x = LSTM(64, return_sequences=False)(x)
    x = Dropout(dropout_rate)(x, training=True) 
    
    # Dense Layers
    x = Dense(32, activation='relu')(x)
    
    # Output Layer
    # We want to predict 'output_steps' days directly
    outputs = Dense(output_steps)(x)
    
    model = Model(inputs=inputs, outputs=outputs)
    
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    
    return model
