class ScoringEngine:
    def __init__(self, exercise_type="LATERAL_RAISE"):
        self.exercise_type = exercise_type
        self.current_score = 100
        self.errors = []
        self.max_angle_in_rep = 0
        self.min_angle_in_rep = 180

    def reset_rep_metrics(self):
        self.max_angle_in_rep = 0
        self.min_angle_in_rep = 180
        self.errors = []

    def process_frame(self, angle, elbow_angle, torso_tilt, stability_variance, state, rep_tempo=None):
        if self.exercise_type == "PUSHUP":
            return self._score_pushup(angle, elbow_angle, torso_tilt, stability_variance, state, rep_tempo)
        else:
            return self._score_lateral_raise(angle, elbow_angle, torso_tilt, stability_variance, state, rep_tempo)

    def _score_pushup(self, angle, elbow_angle, torso_tilt, stability_variance, state, rep_tempo):
        raw_scores = {'rom': 40, 'plank': 30, 'stability': 20, 'tempo': 10}
        
        if angle < self.min_angle_in_rep:
            self.min_angle_in_rep = angle

        # 1. Depth ROM (40pts)
        if state == "BOTTOM":
            if angle > 95:
                raw_scores['rom'] -= min(40, (angle - 95) * 2)
        
        # 2. Plank Integrity (30pts) - Torso tilt deviation from horizontal/baseline
        if torso_tilt > 20:
            raw_scores['plank'] = 0
        elif torso_tilt > 5:
            raw_scores['plank'] = max(0, 30 - (torso_tilt - 5) * 2)

        # 3. Stability (20pts)
        if stability_variance < 3:
            raw_scores['stability'] = 20
        else:
            raw_scores['stability'] = max(0, 20 - (stability_variance - 3) * 3)

        # 4. Tempo (10pts)
        if rep_tempo:
            if rep_tempo < 1.0: raw_scores['tempo'] = 0
            elif rep_tempo < 2.5: raw_scores['tempo'] = 10
            else: raw_scores['tempo'] = 5 # Too slow

        self.current_score = int(sum(raw_scores.values()))
        return self.current_score, self.errors

    def _score_lateral_raise(self, angle, elbow_angle, torso_tilt, stability_variance, state, rep_tempo):
        raw_scores = {'rom': 40, 'elbow': 20, 'torso': 20, 'stability': 10, 'tempo': 10}
        
        if angle > self.max_angle_in_rep:
            self.max_angle_in_rep = angle

        # Shoulder ROM (40pts)
        if state == "HOLD":
            diff = abs(angle - 90)
            if diff > 5:
                raw_scores['rom'] -= min(40, (diff - 5) * 3)
        elif state == "LIFTING" and angle > 110:
            raw_scores['rom'] -= 10
        
        # Elbow Integrity (20pts)
        if elbow_angle < 155:
            raw_scores['elbow'] = 0
        elif elbow_angle < 165:
            raw_scores['elbow'] = max(0, (elbow_angle - 155) * 2)

        # Torso Control (20pts)
        if torso_tilt > 15:
            raw_scores['torso'] = 0
        elif torso_tilt > 5:
            raw_scores['torso'] = max(0, 20 - (torso_tilt - 5) * 2)

        # Stability (10pts)
        if stability_variance < 2:
            raw_scores['stability'] = 10
        else:
            raw_scores['stability'] = max(0, 10 - (stability_variance - 2) * 2)

        # Tempo (10pts)
        if rep_tempo:
            if rep_tempo < 1.2: raw_scores['tempo'] = 0
            else: raw_scores['tempo'] = 10

        self.current_score = int(sum(raw_scores.values()))
        return self.current_score, self.errors

