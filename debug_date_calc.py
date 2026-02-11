
import pandas as pd
import numpy as np
from datetime import datetime

# 1. Create a date range (nanoseconds precision by default)
dates = pd.date_range(end=pd.Timestamp.now(), periods=5, freq='D')
df = pd.DataFrame({'open_time': dates})

print(f"Original Time (first): {df['open_time'].iloc[0]}")
print(f"Dtype: {df['open_time'].dtype}")

# 2. Test conversion (My logic)
try:
    # Method A: astype(np.int64) -> Usually nanoseconds
    ms_a = df['open_time'].astype(np.int64) // 10**6
    print(f"Method A (astype int64 // 10^6): {ms_a.iloc[0]}")
    
    # Method B: .view(np.int64) -> Usually nanoseconds
    ms_b = df['open_time'].values.view(np.int64) // 10**6
    print(f"Method B (view int64 // 10^6): {ms_b[0]}")
    
    # Check if it looks like a valid millisecond timestamp
    # Current timestamp in ms is approx 1.7 * 10^12
    val = ms_a.iloc[0]
    if val > 1_000_000_000_000:
        print("RESULT: Conversion is correct (milliseconds).")
    elif val > 1_000_000_000:
        print("RESULT: Conversion is likely SECONDS (10^9).")
    else:
        print(f"RESULT: Conversion is extremely small ({val}). Likely 1970.")

except Exception as e:
    print(f"Error: {e}")
