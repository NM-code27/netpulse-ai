"""
Rolling feature engineering, used identically at training time (on historical
parquet data) and inference time (on the last ~15 live readings pulled from
the DB) -- the same function must produce the same columns in both places or
the model sees a distribution shift it was never trained on.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["value", "roll_mean_5", "roll_std_5", "roll_mean_15", "rate_of_change", "hour_sin", "hour_cos"]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """df needs columns ['timestamp', 'value'], sorted ascending by timestamp."""
    out = df.copy()
    out["roll_mean_5"] = out["value"].rolling(5, min_periods=1).mean()
    out["roll_std_5"] = out["value"].rolling(5, min_periods=1).std().fillna(0.0)
    out["roll_mean_15"] = out["value"].rolling(15, min_periods=1).mean()
    out["rate_of_change"] = out["value"].diff().fillna(0.0)
    hour = out["timestamp"].dt.hour + out["timestamp"].dt.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return out


def last_feature_row(feat_df: pd.DataFrame) -> pd.Series:
    """
    The single most recent row, restricted to FEATURE_COLUMNS, as a clean
    float64 Series. Selecting a row via .iloc[-1] directly from a frame that
    still has the non-numeric `timestamp` column forces pandas to upcast
    that row to dtype=object (a Series can only hold one dtype, and it can't
    losslessly mix a Timestamp with floats) -- which scikit-learn tolerates
    (it casts internally) but xgboost's inplace_predict rejects outright.
    Selecting the float columns FIRST, then the row, avoids the mixed dtype
    ever being created.
    """
    return feat_df[FEATURE_COLUMNS].iloc[-1]
