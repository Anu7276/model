import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score, roc_curve, auc
import joblib
import os

# Set up directories
os.makedirs("models", exist_ok=True)
os.makedirs("plots", exist_ok=True)

# Load dataset
dataset_path = "../bp/hypertension_dataset.csv"
print(f"Loading dataset from {dataset_path}...")
df = pd.read_csv(dataset_path)

# --- Data Preprocessing ---
print("\n--- Data Preprocessing ---")
# Remove BP_History to avoid data leakage
df.drop("BP_History", axis=1, inplace=True)
# Encode Target
df["Has_Hypertension"] = df["Has_Hypertension"].map({"No": 0, "Yes": 1})
# One-Hot Encoding
df = pd.get_dummies(df, drop_first=True)

# Split Features & Target
X = df.drop("Has_Hypertension", axis=1)
y = df["Has_Hypertension"]

# Save feature columns for schema hardening
joblib.dump(X.columns, "models/feature_columns.pkl")

# Train-Test Split (with stratification)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Feature Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# --- Hyperparameter Tuning (Standardization) ---
print("\n--- Hyperparameter Tuning (Hypertension Model) ---")
param_dist = {
    'n_estimators': [100, 200, 300],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
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
    scoring='f1' # Balance precision and recall
)

rf_random.fit(X_train_scaled, y_train)
best_rf_bp = rf_random.best_estimator_
print(f"Best Parameters: {rf_random.best_params_}")

# --- Evaluation ---
y_prob_rf = best_rf_bp.predict_proba(X_test_scaled)[:, 1]
# Standardized Threshold 0.5 (or keep probability thresholds for risk categorization)
y_pred_standard = (y_prob_rf >= 0.5).astype(int)

print("\nOptimized BP Model Evaluation:")
print("Classification Report:\n", classification_report(y_test, y_pred_standard))

# --- Visualization ---
# Feature Importance
importance = best_rf_bp.feature_importances_
feat_importance = pd.DataFrame({'Feature': X.columns, 'Importance': importance}).sort_values(by='Importance', ascending=False)
plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=feat_importance)
plt.title('Standardized BP Feature Importance')
plt.tight_layout()
plt.savefig("plots/feature_importance_bp_optimized.png")
plt.close()

# --- Saving Artifacts ---
joblib.dump(best_rf_bp, "models/bp_model.pkl")
joblib.dump(scaler, "models/scaler.pkl")

print("\nOptimized BP model and standardized artifacts saved.")
