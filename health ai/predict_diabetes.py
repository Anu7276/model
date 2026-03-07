import joblib
import numpy as np
import pandas as pd

# Load the best model (Random Forest usually outperforms Logistic Regression)
# Using Random Forest for better accuracy while maintaining probability output
MODEL_PATH = "models/diabetes_model_rf.pkl"
SCALER_PATH = "models/scaler.pkl"

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

def predict_diabetes(data):
    """
    Predicts the probability of diabetes based on input features and returns a risk category.
    
    Expected features order (match training):
    [gender, age, hypertension, heart_disease, bmi, HbA1c_level, blood_glucose_level, 
     smoking_history_current, smoking_history_ever, smoking_history_former, 
     smoking_history_never, smoking_history_not current]
    """
    # Convert list to array and reshape
    data_array = np.array(data).reshape(1, -1)
    
    # Scale features
    data_scaled = scaler.transform(data_array)
    
    # Predict probability (Class 1 is diabetes)
    prob = model.predict_proba(data_scaled)[0][1]
    
    # Categorize Risk
    if prob < 0.2:
        risk_category = "Low Risk"
    elif prob < 0.5:
        risk_category = "Moderate Risk"
    else:
        risk_category = "High Risk"
    
    return round(prob * 100, 2), risk_category

if __name__ == "__main__":
    # Example input: Female (1), 44yo, No hypertension (0), No heart disease (0), 
    # BMI 26.54, HbA1c 6.6, Glucose 145, 
    # smoking_history: never (0, 0, 0, 1, 0)
    
    # Dummy features for 'never' smoking history (based on alphabetical order of unique values)
    # current, ever, former, never, not current
    sample_features = [1, 44.0, 0, 0, 26.54, 6.6, 145, 0, 0, 0, 1, 0]
    
    risk_percentage, risk_cat = predict_diabetes(sample_features)
    print(f"Sample Diabetes Risk: {risk_percentage}% ({risk_cat})")
