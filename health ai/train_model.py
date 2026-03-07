import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, roc_curve, auc, recall_score, precision_score
import joblib
import os

# Create folders for models and plots
os.makedirs("models", exist_ok=True)
os.makedirs("plots", exist_ok=True)

# Load dataset
dataset_path = "diabetes_prediction_dataset.csv/diabetes_prediction_dataset.csv"
df = pd.read_csv(dataset_path)

# --- Data Preprocessing ---
print("\n--- Data Preprocessing ---")
df["gender"] = df["gender"].map({"Male": 0, "Female": 1, "Other": 2})
df = pd.get_dummies(df, columns=["smoking_history"], drop_first=True)

# Split Features & Target
X = df.drop("diabetes", axis=1)
y = df["diabetes"]

# Save feature columns for schema hardening
joblib.dump(X.columns, "models/feature_columns.pkl")

# Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Feature Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# --- Hyperparameter Tuning (Standardization) ---
print("\n--- Hyperparameter Tuning (Random Forest) ---")
param_dist = {
    'n_estimators': [100, 200, 300],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'class_weight': ['balanced', 'balanced_subsample']
}

rf_base = RandomForestClassifier(random_state=42)
rf_random = RandomizedSearchCV(
    estimator=rf_base, 
    param_distributions=param_dist, 
    n_iter=10, 
    cv=3, 
    random_state=42, 
    n_jobs=-1,
    scoring='recall' # Optimize for recall in medical context
)

rf_random.fit(X_train_scaled, y_train)
best_rf = rf_random.best_estimator_
print(f"Best Parameters: {rf_random.best_params_}")

# --- Evaluation ---
rf_prob = best_rf.predict_proba(X_test_scaled)[:, 1]
# Standardized Risk Categorization: Low < 0.2, Moderate < 0.5, High >= 0.5
rf_pred_standard = (rf_prob >= 0.5).astype(int)

print("\nOptimized Random Forest Evaluation:")
print("Accuracy:", accuracy_score(y_test, rf_pred_standard))
print("Classification Report:\n", classification_report(y_test, rf_pred_standard))

# --- Visualization ---
# ROC Curve
fpr, tpr, _ = roc_curve(y_test, rf_prob)
roc_auc = auc(fpr, tpr)
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC)')
plt.legend(loc="lower right")
plt.savefig("plots/roc_curve_optimized.png")
plt.close()

# Feature Importance
importance = best_rf.feature_importances_
feat_importance = pd.DataFrame({'Feature': X.columns, 'Importance': importance}).sort_values(by='Importance', ascending=False)
plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=feat_importance)
plt.title('Standardized Feature Importance')
plt.tight_layout()
plt.savefig("plots/feature_importance_optimized.png")
plt.close()

# --- Saving Artifacts ---
joblib.dump(best_rf, "models/diabetes_model_rf.pkl")
joblib.dump(scaler, "models/scaler.pkl")

print("\nOptimized Diabetes model and standardized artifacts saved.")
