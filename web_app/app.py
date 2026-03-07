from flask import Flask, render_template, request, jsonify
import joblib
import numpy as np
import pandas as pd
import os
import sys
import time

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXERCISE_AI_PATH = os.path.join(BASE_DIR, "posture", "exercise_ai")
sys.path.append(EXERCISE_AI_PATH)

from squat_v2 import SquatV2Coach
from pushup_v2 import PushupV2Coach
from side_arm_v2 import SideArmV2Coach

# Production-Grade Session Management
ACTIVE_SESSIONS = {}

def get_session_id():
    # In production, this would use a session cookie or JWT
    return request.remote_addr

def get_coach(ex_type):
    sid = get_session_id()
    session_key = f"{sid}_{ex_type}"
    
    if session_key not in ACTIVE_SESSIONS:
        if ex_type == 'squat': ACTIVE_SESSIONS[session_key] = SquatV2Coach()
        elif ex_type == 'pushup': ACTIVE_SESSIONS[session_key] = PushupV2Coach()
        else: ACTIVE_SESSIONS[session_key] = SideArmV2Coach()
        
    return ACTIVE_SESSIONS[session_key]

app = Flask(__name__)

DIABETES_MODELS = os.path.join(BASE_DIR, "health ai", "models")
BP_MODELS = os.path.join(BASE_DIR, "bp_model", "models")
OBESITY_MODELS = os.path.join(BASE_DIR, "obesity_model", "models")

def load_standard_artifacts(directory, model_name):
    model = joblib.load(os.path.join(directory, f"{model_name}.pkl"))
    scaler = joblib.load(os.path.join(directory, "scaler.pkl"))
    feature_cols = joblib.load(os.path.join(directory, "feature_columns.pkl"))
    return model, scaler, feature_cols

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict/diabetes', methods=['POST'])
def predict_diabetes():
    try:
        data = request.json
        model, scaler, feature_cols = load_standard_artifacts(DIABETES_MODELS, "diabetes_model_rf")
        
        input_dict = {
            'gender': {"Male": 0, "Female": 1, "Other": 2}.get(data['gender'], 1),
            'age': float(data['age']),
            'hypertension': 1 if data['hypertension'] == "Yes" else 0,
            'heart_disease': 1 if data['heart_disease'] == "Yes" else 0,
            'bmi': float(data['bmi']),
            'HbA1c_level': float(data['hba1c']),
            'blood_glucose_level': float(data['glucose']),
            'smoking_history': data['smoking_history']
        }
        
        df_input = pd.DataFrame([input_dict])
        df_encoded = pd.get_dummies(df_input)
        df_final = df_encoded.reindex(columns=feature_cols, fill_value=0)
        
        X_scaled = scaler.transform(df_final)
        prob = model.predict_proba(X_scaled)[0][1]
        
        risk = "Low Risk" if prob < 0.2 else ("Moderate Risk" if prob < 0.5 else "High Risk")
        return jsonify({
            "probability": round(prob * 100, 2),
            "risk_category": risk,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/predict/bp', methods=['POST'])
def predict_bp():
    try:
        data = request.json
        model, scaler, feature_cols = load_standard_artifacts(BP_MODELS, "bp_model")
        
        input_dict = {
            'Age': float(data['age']), 'Daily_Salt_Intake': float(data['salt']),
            'Stress_Level': float(data['stress']), 'Avg_Sleep_Hours': float(data['sleep']),
            'BMI': float(data['bmi']), 'Medication': data['medication'],
            'Family_History': data['family_history'], 'Exercise_Level': data['exercise'],
            'Smoking_Status': data['smoking']
        }
        
        df_input = pd.DataFrame([input_dict])
        df_encoded = pd.get_dummies(df_input)
        df_final = df_encoded.reindex(columns=feature_cols, fill_value=0)
        
        X_scaled = scaler.transform(df_final)
        prob = model.predict_proba(X_scaled)[0][1]
        
        risk = "Low" if prob < 0.25 else ("Elevated" if prob < 0.6 else "High")
        return jsonify({
            "probability": round(prob * 100, 2),
            "risk_category": risk,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/predict/obesity', methods=['POST'])
def predict_obesity():
    try:
        data = request.json
        model, scaler, feature_cols = load_standard_artifacts(OBESITY_MODELS, "obesity_model")
        le = joblib.load(os.path.join(OBESITY_MODELS, "label_encoder.pkl"))
        
        input_data = {
            'Age': float(data['age']), 'Height': float(data['height']), 'Weight': float(data['weight']),
            'FCVC': float(data['fcvc']), 'NCP': float(data['ncp']), 'CH2O': float(data['ch2o']),
            'FAF': float(data['faf']), 'TUE': float(data['tue']),
            'Gender': data['gender'], 'Family_history_with_overweight': data['family_history'],
            'FAVC': data['favc'], 'CAEC': data['caec'], 'SMOKE': data['smoking'],
            'SCC': data['scc'], 'MTRANS': data['mtrans'], 'CALC': data['calc']
        }
        
        df_input = pd.DataFrame([input_data])
        df_encoded = pd.get_dummies(df_input)
        df_final = df_encoded.reindex(columns=feature_cols, fill_value=0)
        
        input_scaled = scaler.transform(df_final)
        pred_num = model.predict(input_scaled)[0]
        label = le.inverse_transform([pred_num])[0]
        
        simplified = "Obese"
        if "Insufficient" in label: simplified = "Underweight"
        elif "Normal" in label: simplified = "Healthy"
        elif "Overweight" in label: simplified = "Overweight"
        
        return jsonify({
            "prediction": label,
            "simplified": simplified,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/process_pose', methods=['POST'])
def process_pose():
    try:
        data = request.json
        ex_type = data.get('exercise_type', 'sidearm')
        raw_landmarks = data.get('landmarks')
        
        if not raw_landmarks:
            return jsonify({"status": "error", "message": "Missing landmarks"}), 400
            
        coach = get_coach(ex_type)
        
        class LandmarkObj:
            def __init__(self, x, y, visibility):
                self.x = x
                self.y = y
                self.visibility = visibility
                
        landmarks = [LandmarkObj(lm['x'], lm['y'], lm.get('visibility', lm.get('score', 1.0))) for lm in raw_landmarks]
        
        stats = coach.process(landmarks)
        
        # Session Metrics
        sid = get_session_id()
        meta_key = f"meta_{sid}"
        if meta_key not in ACTIVE_SESSIONS:
             ACTIVE_SESSIONS[meta_key] = {'start': time.time(), 'history': []}
             
        session_meta = ACTIVE_SESSIONS[meta_key]
        stats['elapsed_time'] = int(time.time() - session_meta['start'])
        session_meta['history'].append(stats.get('form_score', 100))
        stats['avg_score'] = sum(session_meta['history']) / len(session_meta['history'])

        return jsonify(stats)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/reset_fitness', methods=['POST'])
def reset_fitness():
    sid = get_session_id()
    to_delete = [k for k in ACTIVE_SESSIONS.keys() if k.startswith(sid) or k.endswith(sid)]
    for k in to_delete: del ACTIVE_SESSIONS[k]
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
