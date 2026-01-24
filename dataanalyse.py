import pandas as pd

# Load the dataset
df = pd.read_csv("students.csv")  # Make sure the file is in your project directory

# Show basic info
print("Dataset:\n", df)

# Mean
print("\nMean:\n", df.mean(numeric_only=True))

# Median
print("\nMedian:\n", df.median(numeric_only=True))

# Min
print("\nMinimum:\n", df.min(numeric_only=True))

# Max
print("\nMaximum:\n", df.max(numeric_only=True))

# Optional: Display subject-wise statistics
print("\nSummary Statistics:\n", df.describe())
