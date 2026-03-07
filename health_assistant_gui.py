import tkinter as tk
from tkinter import ttk, messagebox
import joblib
import numpy as np
import pandas as pd
import os

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIABETES_MODELS = os.path.join(BASE_DIR, "health ai", "models")
BP_MODELS = os.path.join(BASE_DIR, "bp_model", "models")
OBESITY_MODELS = os.path.join(BASE_DIR, "obesity_model", "models")

class HealthAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced AI Health Assistant - Optimized")
        self.root.geometry("850x750")
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background="#f8f9fa")
        self.style.configure("TFrame", background="#f8f9fa")
        self.style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), background="#f8f9fa", foreground="#2c3e50")
        self.style.configure("Subheader.TLabel", font=("Helvetica", 12, "bold"), background="#f8f9fa", foreground="#34495e")
        self.style.configure("Result.TLabel", font=("Helvetica", 13, "bold"), background="#f8f9fa", foreground="#27ae60")
        
        # Create Notebook for Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=15, pady=15)
        
        # Tabs initialization
        self.tab_diabetes = ttk.Frame(self.notebook); self.notebook.add(self.tab_diabetes, text="  Diabetes  ")
        self.tab_bp = ttk.Frame(self.notebook); self.notebook.add(self.tab_bp, text="  Hypertension  ")
        self.tab_obesity = ttk.Frame(self.notebook); self.notebook.add(self.tab_obesity, text="  Obesity  ")

        self.setup_diabetes_ui()
        self.setup_bp_ui()
        self.setup_obesity_ui()

    def load_artifacts(self, directory, model_name):
        model = joblib.load(os.path.join(directory, f"{model_name}.pkl"))
        scaler = joblib.load(os.path.join(directory, "scaler.pkl"))
        feature_cols = joblib.load(os.path.join(directory, "feature_columns.pkl"))
        return model, scaler, feature_cols

    # --- DIABETES SECTION ---
    def setup_diabetes_ui(self):
        container = ttk.Frame(self.tab_diabetes, padding=25)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text="Diabetes Risk Assessment", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        self.db_vars = {
            "gender": tk.StringVar(value="Female"),
            "hypertension": tk.StringVar(value="No"),
            "heart": tk.StringVar(value="No")
        }
        
        self.db_inputs = {}
        fields = [("Age", "years"), ("BMI", "score"), ("HbA1c", "level"), ("Glucose", "mg/dL")]
        for i, (name, unit) in enumerate(fields):
            ttk.Label(container, text=f"{name} ({unit}):", style="Subheader.TLabel").grid(row=i+1, column=0, sticky='w', pady=8)
            ent = ttk.Entry(container, width=35); ent.grid(row=i+1, column=1, padx=10, sticky='w')
            self.db_inputs[name] = ent
            
        ttk.Label(container, text="Smoking History:", style="Subheader.TLabel").grid(row=5, column=0, sticky='w', pady=10)
        self.db_smoking = ttk.Combobox(container, values=["never", "current", "former", "ever", "not current"], width=32, state="readonly")
        self.db_smoking.grid(row=5, column=1, padx=10, sticky='w'); self.db_smoking.set("never")

        ttk.Button(container, text="Analyze Diabetes Risk", command=self.predict_diabetes).grid(row=10, column=0, columnspan=2, pady=30)
        self.db_res = ttk.Label(container, text="", style="Result.TLabel"); self.db_res.grid(row=11, column=0, columnspan=2)

    def predict_diabetes(self):
        try:
            model, scaler, feature_cols = self.load_artifacts(DIABETES_MODELS, "diabetes_model_rf")
            input_dict = {
                'gender': {"Male": 0, "Female": 1, "Other": 2}.get(self.db_vars["gender"].get(), 1),
                'age': float(self.db_inputs["Age"].get()),
                'hypertension': 1 if self.db_vars["hypertension"].get() == "Yes" else 0,
                'heart_disease': 1 if self.db_vars["heart"].get() == "Yes" else 0,
                'bmi': float(self.db_inputs["BMI"].get()),
                'HbA1c_level': float(self.db_inputs["HbA1c"].get()),
                'blood_glucose_level': float(self.db_inputs["Glucose"].get()),
                'smoking_history': self.db_smoking.get()
            }
            df_final = pd.get_dummies(pd.DataFrame([input_dict])).reindex(columns=feature_cols, fill_value=0)
            prob = model.predict_proba(scaler.transform(df_final))[0][1]
            
            risk = "Low Risk" if prob < 0.2 else ("Moderate Risk" if prob < 0.5 else "High Risk")
            color = "#27ae60" if prob < 0.2 else ("#f39c12" if prob < 0.5 else "#e74c3c")
            self.db_res.config(text=f"Risk: {prob*100:.1f}% — {risk}", foreground=color)
        except Exception as e: messagebox.showerror("Error", str(e))

    # --- BP SECTION ---
    def setup_bp_ui(self):
        container = ttk.Frame(self.tab_bp, padding=25)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text="Hypertension Risk Diagnosis", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        self.bp_inputs = {}
        fields = [("Age", ""), ("Salt Intake", "(g)"), ("Stress level", "(1-10)"), ("Sleep", "(hrs)"), ("BMI", "")]
        for i, (name, unit) in enumerate(fields):
            ttk.Label(container, text=f"{name} {unit}:", style="Subheader.TLabel").grid(row=i+1, column=0, sticky='w', pady=8)
            ent = ttk.Entry(container, width=35); ent.grid(row=i+1, column=1, padx=10, sticky='w')
            self.bp_inputs[name] = ent

        ttk.Label(container, text="Medication:", style="Subheader.TLabel").grid(row=6, column=0, sticky='w'); self.bp_med = ttk.Combobox(container, values=["None", "Other"], width=32); self.bp_med.grid(row=6, column=1); self.bp_med.set("None")
        ttk.Label(container, text="Exercise:", style="Subheader.TLabel").grid(row=7, column=0, sticky='w'); self.bp_ex = ttk.Combobox(container, values=["Low", "Moderate", "High"], width=32); self.bp_ex.grid(row=7, column=1); self.bp_ex.set("Moderate")

        ttk.Button(container, text="Calculate BP Risk", command=self.predict_bp).grid(row=10, column=0, columnspan=2, pady=25)
        self.bp_res = ttk.Label(container, text="", style="Result.TLabel"); self.bp_res.grid(row=11, column=0, columnspan=2)

    def predict_bp(self):
        try:
            model, scaler, feature_cols = self.load_artifacts(BP_MODELS, "bp_model")
            input_dict = {
                'Age': float(self.bp_inputs["Age"].get()), 'Daily_Salt_Intake': float(self.bp_inputs["Salt Intake"].get()),
                'Stress_Level': float(self.bp_inputs["Stress level"].get()), 'Avg_Sleep_Hours': float(self.bp_inputs["Sleep"].get()),
                'BMI': float(self.bp_inputs["BMI"].get()), 'Medication': self.bp_med.get(),
                'Family_History': "No", 'Exercise_Level': self.bp_ex.get(), 'Smoking_Status': "Non-Smoker"
            }
            df_final = pd.get_dummies(pd.DataFrame([input_dict])).reindex(columns=feature_cols, fill_value=0)
            prob = model.predict_proba(scaler.transform(df_final))[0][1]
            
            risk = "Low" if prob < 0.25 else ("Elevated" if prob < 0.6 else "High")
            color = "#27ae60" if prob < 0.25 else ("#f39c12" if prob < 0.6 else "#e74c3c")
            self.bp_res.config(text=f"Risk: {prob*100:.1f}% — {risk}", foreground=color)
        except Exception as e: messagebox.showerror("Error", str(e))

    # --- OBESITY SECTION ---
    def setup_obesity_ui(self):
        container = ttk.Frame(self.tab_obesity, padding=20)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text="Obesity & Healthy Weight Analysis", style="Header.TLabel").pack(pady=10)
        
        # Using a simplified layout for Obesity in the GUI for brevity, matching the web app's logic
        form = ttk.Frame(container)
        form.pack(fill='both', expand=True)
        
        self.ob_inputs = {}
        for i, (name, unit) in enumerate([("Age", "yrs"), ("Height", "m"), ("Weight", "kg")]):
            row = ttk.Frame(form); row.pack(fill='x', pady=5)
            ttk.Label(row, text=f"{name} ({unit}):", width=15).pack(side='left')
            ent = ttk.Entry(row); ent.pack(side='left', padx=10, expand=True, fill='x')
            self.ob_inputs[name] = ent

        ttk.Button(container, text="Generate Obesity Report", command=self.predict_obesity).pack(pady=20)
        self.ob_res = ttk.Label(container, text="", style="Result.TLabel"); self.ob_res.pack()

    def predict_obesity(self):
        try:
            model, scaler, feature_cols = self.load_artifacts(OBESITY_MODELS, "obesity_model")
            le = joblib.load(os.path.join(OBESITY_MODELS, "label_encoder.pkl"))
            
            # Simplified mock for other fields to ensure schema compatibility
            input_dict = {
                'Age': float(self.ob_inputs["Age"].get()), 'Height': float(self.ob_inputs["Height"].get()), 'Weight': float(self.ob_inputs["Weight"].get()),
                'FCVC': 2.0, 'NCP': 3.0, 'CH2O': 2.0, 'FAF': 1.0, 'TUE': 1.0, 'Gender': 'Female',
                'Family_history_with_overweight': 'yes', 'FAVC': 'yes', 'CAEC': 'Sometimes', 'SMOKE': 'no',
                'SCC': 'no', 'MTRANS': 'Public_Transportation', 'CALC': 'no'
            }
            df_final = pd.get_dummies(pd.DataFrame([input_dict])).reindex(columns=feature_cols, fill_value=0)
            pred = model.predict(scaler.transform(df_final))[0]
            label = le.inverse_transform([pred])[0]
            
            self.ob_res.config(text=f"Status: {label}")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = HealthAssistantApp(root)
    root.mainloop()
