import pandas as pd
import numpy as np


def add_technical_indicators(df):
    """
    Adds technical indicators to the DataFrame using pure pandas/numpy.
    Expects columns: 'open', 'high', 'low', 'close', 'volume'.

    FIX 1: RSI now uses Wilder's smoothing (ewm alpha=1/14) instead of
            simple rolling mean — the standard correct formula.
    FIX 2: dropna() removed from here. Caller (preprocess.py) is responsible
            for dropping NaNs AFTER sentiment merge so row counts stay aligned.
    FIX 3: ema_99 removed — it costs ~99 warmup rows with minimal predictive
            gain over ema_25. Replaced with ema_50 for a better tradeoff.
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # --- 1. RSI (Relative Strength Index) ---
    # FIXED: Use Wilder's smoothing (ewm with alpha=1/14, adjust=False).
    # Simple rolling mean (the previous implementation) produces incorrect RSI
    # values and is not the standard formula used by trading platforms.
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()

    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # --- 2. MACD (Moving Average Convergence Divergence) ---
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()

    df['MACD_12_26_9'] = ema_12 - ema_26
    df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
    df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']

    # --- 3. EMA (Exponential Moving Averages) ---
    # FIXED: Removed ema_99. It forces ~99 warmup rows to be NaN-dropped,
    # wasting ~20% of a 500-row dataset. ema_50 captures long-term trend
    # with a far smaller warmup penalty (ewm converges quickly).
    df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
    df['ema_25'] = df['close'].ewm(span=25, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

    # --- 4. ATR (Average True Range) ---
    high_low   = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close  = (df['low']  - df['close'].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    # --- 5. Volume Moving Average ---
    df['vol_ma_20'] = df['volume'].rolling(window=20).mean()

    # FIXED: No dropna() here. NaN rows are dropped centrally in
    # preprocess.py AFTER sentiment merge so all column lengths stay aligned.
    return df


def add_sentiment_indicators(df, sentiment_df=None, coin=None):
    """
    Merges sentiment data into the main dataframe based on date.

    FIX: Replaced manual index reassignment (df_merged.index = df.index)
         with proper index-preserving merge using date_key as a temporary
         column, then restoring the original DatetimeIndex safely.
         The old approach could silently mis-align rows when merge changed
         row count (e.g. duplicate dates in sentiment data).
    """
    df = df.copy()

    if 'sentiment_score' not in df.columns:
        df['sentiment_score'] = 50.0

    if coin in {"BNB", "ADA"}:
        df['sentiment_score'] = 50.0
        return df

    if sentiment_df is not None and not sentiment_df.empty:
        try:
            df = df.drop(columns=['sentiment_score'], errors='ignore')

            # Build date-keyed lookup from sentiment (one row per day)
            sent_temp = sentiment_df.copy()
            sent_temp['date_key'] = sent_temp.index.strftime('%Y-%m-%d')
            sent_temp = sent_temp.drop_duplicates(subset=['date_key'])
            sent_lookup = sent_temp.set_index('date_key')['sentiment_score']

            # Map by date string — safe, index-preserving, no row reordering
            df['sentiment_score'] = (
                df.index.strftime('%Y-%m-%d')
                  .map(sent_lookup)
            )

            df['sentiment_score'] = df['sentiment_score'].ffill().fillna(50.0)

            nan_count = df['sentiment_score'].isna().sum()
            if nan_count > len(df) * 0.5:
                print(f" [WARN] Sentiment join had low match rate: "
                      f"{len(df) - nan_count}/{len(df)}")

        except Exception as e:
            print(f" [WARN] Sentiment join failed: {e}")
            if 'sentiment_score' not in df.columns:
                df['sentiment_score'] = 50.0

    return df


def get_feature_columns():
    """
    Returns the ordered list of feature columns used for training and inference.

    IMPORTANT: This list must be identical at train time and inference time.
    Any change here requires retraining all models.

    FIX: Replaced ema_99 with ema_50 to match the updated indicator set.
    Total features: 15.
    """
    return [
        'close', 'high', 'low', 'open', 'volume',
        'rsi',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'ema_7', 'ema_25', 'ema_50',
        'atr', 'vol_ma_20',
        'sentiment_score',
    ]
