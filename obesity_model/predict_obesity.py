import pandas as pd
import numpy as np
import joblib
import os

def load_artifacts():
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, "models")
    
    model = joblib.load(os.path.join(models_dir, "obesity_model.pkl"))
    scaler = joblib.load(os.path.join(models_dir, "scaler.pkl"))
    le = joblib.load(os.path.join(models_dir, "label_encoder.pkl"))
    feature_columns = joblib.load(os.path.join(models_dir, "feature_columns.pkl"))
    
    return model, scaler, le, feature_columns

def simplify_category(label):
    if "Insufficient" in label:
        return "Underweight"
    elif "Normal" in label:
        return "Healthy"
    elif "Overweight" in label:
        return "Overweight"
    else:
        return "Obese"

def predict(input_dict):
    """
    Predicts obesity level and risk category from raw input features.
    input_dict: Dictionary containing raw feature values (e.g., {'Age': 21, 'Gender': 'Male', ...})
    """
    model, scaler, le, feature_columns = load_artifacts()
    
    # 1. Convert to DataFrame
    df_input = pd.DataFrame([input_dict])
    
    # 2. Replicate One-Hot Encoding used in training
    # During training, we used: df = pd.get_dummies(df, drop_first=True)
    df_encoded = pd.get_dummies(df_input)
    
    # 3. Schema Hardening: Reindex with training feature names
    # This aligns the columns and fills missing dummies with 0
    df_final = df_encoded.reindex(columns=feature_columns, fill_value=0)
    
    # 4. Scale the features
    input_scaled = scaler.transform(df_final)
    
    # 5. Predict
    prediction_numeric = model.predict(input_scaled)[0]
    prediction_label = le.inverse_transform([prediction_numeric])[0]
    
    # 6. Simplify for UI
    risk_category = simplify_category(prediction_label)
    
    return {
        "prediction": prediction_label,
        "risk_category": risk_category
    }

if __name__ == "__main__":
    # Robust demonstration with one of the most common medical inputs
    # Use real feature names expected by the model
    example_input = {
        'Age': 21.0,
        'Gender': 'Male',
        'Height': 1.62,
        'Weight': 64.0,
        'family_history_with_overweight': 'yes',
        'FAVC': 'no',
        'FCVC': 2.0,
        'NCP': 3.0,
        'CAEC': 'Sometimes',
        'SMOKE': 'no',
        'CH2O': 2.0,
        'SCC': 'no',
        'FAF': 0.0,
        'TUE': 1.0,
        'CALC': 'no',
        'MTRANS': 'Public_Transportation'
    }
    
    print("--- Obesity Prediction Demo ---")
    try:
        result = predict(example_input)
        print(f"Input: {example_input['Weight']}kg, {example_input['Height']}m, {example_input['Age']} years")
        print(f"Predicted Class: {result['prediction']}")
        print(f"Risk Category:  {result['risk_category']}")
    except Exception as e:
        print(f"Error during prediction: {e}")
