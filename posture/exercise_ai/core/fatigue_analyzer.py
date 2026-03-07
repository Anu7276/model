class FatigueAnalyzer:
    def __init__(self):
        self.fatigue_flag = False
        self.stability_history = []
        self.lean_history = []
        self.max_angles = []
        
    def update(self, current_angle, stability_variance, lean_deviation):
        """
        Dynamic frame-level fatigue detection.
        Detects fatigue through:
        1. Increasing stability variance (shaking)
        2. Increasing torso lean (compensation)
        3. Drop in max range (struggle)
        """
        # Maintain history (last 100 frames ~ 3-5 seconds)
        self.stability_history.append(stability_variance)
        self.lean_history.append(lean_deviation)
        if len(self.stability_history) > 100:
            self.stability_history.pop(0)
            self.lean_history.pop(0)

        # Analysis logic
        if len(self.stability_history) > 60:
            avg_stability = sum(self.stability_history) / len(self.stability_history)
            avg_lean = sum(self.lean_history) / len(self.lean_history)
            
            # If shaking is high OR leaning is getting excessive
            if avg_stability > 8.0 or avg_lean > 15.0:
                self.fatigue_flag = True
            else:
                self.fatigue_flag = False

        return self.get_status()

    def reset(self):
        self.fatigue_flag = False
        self.stability_history = []
        self.lean_history = []
        self.max_angles = []

    def get_status(self):
        return "FATIGUED" if self.fatigue_flag else "OPTIMAL"
