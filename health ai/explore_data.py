import pandas as pd

# Load dataset
df = pd.read_csv("diabetes_prediction_dataset.csv/diabetes_prediction_dataset.csv")

print("--- Head ---")
print(df.head())

print("\n--- Info ---")
print(df.info())

print("\n--- Describe ---")
print(df.describe())

print("\n--- Class Balance ---")
print(df["diabetes"].value_counts())

print("\n--- Missing Values ---")
print(df.isnull().sum())
