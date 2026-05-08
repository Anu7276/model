from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import joblib
import numpy as np
import pandas as pd
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXERCISE_AI_PATH = os.path.join(BASE_DIR, "posture", "exercise_ai")
sys.path.append(EXERCISE_AI_PATH)

from squat_v2 import SquatV2Coach
from pushup_v2 import PushupV2Coach
from side_arm_v2 import SideArmV2Coach

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

# Enable CORS for frontend development
CORS(app)

# Initialize Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[os.getenv('RATELIMIT_DEFAULT', "100/day")],
    storage_uri="memory://",
)

# Production-Grade Session Management
ACTIVE_SESSIONS = {}

def get_session_id():
    # In production, we'd extract user_id from Supabase JWT
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        # Placeholder for JWT verification
        # For now, we still use IP but identify it's ready for tokens
        pass
    return request.remote_addr

def get_coach(ex_type):
    sid = get_session_id()
    session_key = f"{sid}_{ex_type}"
    
    if session_key not in ACTIVE_SESSIONS:
        if ex_type == 'squat': ACTIVE_SESSIONS[session_key] = SquatV2Coach()
        elif ex_type == 'pushup': ACTIVE_SESSIONS[session_key] = PushupV2Coach()
        else: ACTIVE_SESSIONS[session_key] = SideArmV2Coach()
        
    return ACTIVE_SESSIONS[session_key]

DIABETES_MODELS = os.path.join(BASE_DIR, "health ai", "models")
BP_MODELS = os.path.join(BASE_DIR, "bp_model", "models")
OBESITY_MODELS = os.path.join(BASE_DIR, "obesity_model", "models")

def load_standard_artifacts(directory, model_name):
    model = joblib.load(os.path.join(directory, f"{model_name}.pkl"))
    scaler = joblib.load(os.path.join(directory, "scaler.pkl"))
    feature_cols = joblib.load(os.path.join(directory, "feature_columns.pkl"))
    return model, scaler, feature_cols

@app.route('/api/predict/diabetes', methods=['POST'])
@limiter.limit(os.getenv('RATELIMIT_PREDICT', "10/minute"))
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

@app.route('/api/predict/bp', methods=['POST'])
@limiter.limit(os.getenv('RATELIMIT_PREDICT', "10/minute"))
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

@app.route('/api/predict/obesity', methods=['POST'])
@limiter.limit(os.getenv('RATELIMIT_PREDICT', "10/minute"))
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

@app.route('/api/process_pose', methods=['POST'])
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

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        data = request.json
        messages = data.get('messages', [])
        
        system_prompt = {
            "role": "system",
            "content": "You are PreventAI, a highly intelligent and empathetic Healthcare Expert and Medical AI. Your goal is to provide accurate, evidence-based health advice. You should: 1. Use clinical language but remain accessible. 2. Always recommend professional consultation for serious symptoms. 3. Suggest reputable web resources (Mayo Clinic, NHS, CDC). 4. Help users understand their health metrics (BMI, Glucose, BP). Keep responses concise and formatted with markdown."
        }
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[system_prompt] + messages,
            temperature=0.7,
            max_tokens=1024,
        )
        
        return jsonify({
            "message": response.choices[0].message.content,
            "status": "success"
        })
    except Exception as e:
        print(f"CHAT ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=port, host='0.0.0.0')
