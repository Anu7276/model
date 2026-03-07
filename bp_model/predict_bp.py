import joblib
import numpy as np
import pandas as pd

# Path to saved model and scaler
MODEL_PATH = "models/bp_model.pkl"
SCALER_PATH = "models/scaler.pkl"

def load_resources():
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        return model, scaler
    except FileNotFoundError:
        print("Model or Scaler not found. Please run train_bp_model.py first.")
        return None, None

def classify_risk(prob):
    """
    Categorizes hypertension risk based on medical probability.
    """
    if prob < 0.25:
        return "Low Risk"
    elif prob < 0.60:
        return "Elevated Risk"
    else:
        return "High Risk"

def predict_bp(data):
    """
    Predicts the risk of hypertension.
    
    Expected features (12 total after dummy encoding):
    1. Age
    2. Salt_Intake
    3. Stress_Score
    4. Sleep_Duration
    5. BMI
    6. Medication_None
    7. Medication_Other
    8. Family_History_Yes
    9. Exercise_Level_Low
    10. Exercise_Level_Moderate
    11. Smoking_Status_Non-Smoker
    12. Smoking_Status_Smoker
    """
    model, scaler = load_resources()
    if model is None or scaler is None:
        return None, None

    # Convert to array and scale
    data_array = np.array(data).reshape(1, -1)
    data_scaled = scaler.transform(data_array)

    # Predict probability
    prob = model.predict_proba(data_scaled)[0][1]
    
    # Classify risk
    risk_cat = classify_risk(prob)
    
    return round(prob * 100, 2), risk_cat

if __name__ == "__main__":
    print("--- Professional BP Prediction Interface ---")
    
    # Example for: Age 45, Salt 10.0, Stress 8, Sleep 6, BMI 29.5
    # Medication: None [1, 0] (Assuming 'None' and 'Other' are the remaining columns)
    # Family History: Yes [1]
    # Exercise: Low [1, 0]
    # Smoking: Smoker [0, 1]
    
    # Feature list (12 features):
    # Age (45), Salt (10.0), Stress (8), Sleep (6), BMI (29.5)
    # Medication_None (1), Medication_Other (0)
    # Family_History_Yes (1)
    # Exercise_Level_Low (1), Exercise_Level_Moderate (0)
    # Smoking_Status_Non-Smoker (0), Smoking_Status_Smoker (1)
    
    sample_features = [45, 10.0, 8, 6, 29.5, 1, 0, 1, 1, 0, 0, 1]
    
    risk_percentage, risk_cat = predict_bp(sample_features)
    if risk_percentage is not None:
        print(f"\nSample BP Risk: {risk_percentage}%")
        print(f"Category: {risk_cat}")
