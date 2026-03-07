import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# Load Dataset
data_path = r"c:\Users\Anurag\OneDrive\Documents\hackthon\obesity\ObesityDataSet_raw_and_data_sinthetic.csv"
df = pd.read_csv(data_path)

print("Dataset loaded successfully.")

# --- Data Preprocessing ---
le = LabelEncoder()
df["NObeyesdad"] = le.fit_transform(df["NObeyesdad"])

# One-Hot Encode Categoricals
df = pd.get_dummies(df, drop_first=True)

# Split Features & Target
X = df.drop("NObeyesdad", axis=1)
y = df["NObeyesdad"]

# Save feature columns for schema hardening
os.makedirs("models", exist_ok=True)
joblib.dump(X.columns, "models/feature_columns.pkl")
joblib.dump(le, "models/label_encoder.pkl")

# Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
joblib.dump(scaler, "models/scaler.pkl")

# --- Hyperparameter Tuning (Standardization) ---
print("\n--- Hyperparameter Tuning (Obesity Model) ---")
param_dist = {
    'n_estimators': [200, 300, 400],
    'max_depth': [None, 15, 25],
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2],
    'class_weight': ['balanced']
}

rf_base = RandomForestClassifier(random_state=42)
rf_random = RandomizedSearchCV(
    estimator=rf_base, 
    param_distributions=param_dist, 
    n_iter=10, 
    cv=3, 
    random_state=42, 
    n_jobs=-1,
    scoring='accuracy'
)

rf_random.fit(X_train_scaled, y_train)
best_rf_ob = rf_random.best_estimator_
print(f"Best Parameters: {rf_random.best_params_}")

# --- Evaluation ---
y_pred = best_rf_ob.predict(X_test_scaled)
print(f"\nOptimized Obesity Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=le.classes_))

# --- Visualization ---
os.makedirs("plots", exist_ok=True)
importances = best_rf_ob.feature_importances_
indices = np.argsort(importances)
plt.figure(figsize=(10, 12))
plt.barh(range(len(indices)), importances[indices])
plt.yticks(range(len(indices)), X.columns[indices])
plt.title("Optimized Feature Importance - Obesity Model")
plt.tight_layout()
plt.savefig("plots/feature_importance_optimized.png")
plt.close()

# --- Saving Artifacts ---
joblib.dump(best_rf_ob, "models/obesity_model.pkl")

print("\nOptimized Obesity model and standardized artifacts saved.")
