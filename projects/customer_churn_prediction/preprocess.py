import pandas as pd
from sklearn.preprocessing import LabelEncoder

def preprocess_data(df):
    # Drop customerID (not useful for prediction)
    if "customerID" in df.columns:
        df = df.drop("customerID", axis=1)

    # Handle missing values
    df = df.dropna()

    # Encode categorical columns
    encoder = LabelEncoder()
    for col in df.select_dtypes(include="object"):
        df[col] = encoder.fit_transform(df[col])

    return df
