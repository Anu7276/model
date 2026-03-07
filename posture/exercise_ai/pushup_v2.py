"""pushup_v2.py
Professional push-up coach with stable rep counting, calibration, scoring, and fatigue tracking.
"""

import time
import numpy as np

from core.angle_engine import calculate_angle, JitterFilter, DynamicBaselineTracker
from core.state_machine import PushupStateMachine, PushupState
from core.stability_tracker import StabilityTracker
from core.scoring_engine import ScoringEngine
from core.fatigue_analyzer import FatigueAnalyzer
from core.session_logger import SessionLogger
from ui.overlay_renderer import OverlayRenderer
from voice import speak


class PushupV2Coach:
    L_SHOULDER = 11
    R_SHOULDER = 12
    L_ELBOW = 13
    R_ELBOW = 14
    L_WRIST = 15
    R_WRIST = 16
    L_HIP = 23
    R_HIP = 24
    L_ANKLE = 27
    R_ANKLE = 28

    MIN_VIS = 0.40
    CALIBRATION_SECONDS = 2.0
    CALIBRATION_MIN_SAMPLES = 12
    MIN_REP_TIME = 0.85
    DEPTH_GOOD_MAX = 105

    def __init__(self):
        self.state_machine = PushupStateMachine()
        self.stability_tracker = StabilityTracker(size=20)
        self.scoring_engine = ScoringEngine(exercise_type="PUSHUP")
        self.fatigue_analyzer = FatigueAnalyzer()
        self.session_logger = SessionLogger()
        self.ui_renderer = OverlayRenderer()

        self.elbow_filter = JitterFilter(alpha=0.10)
        self.plank_tracker = DynamicBaselineTracker(alpha=0.30)

        self.rep_start_time = None
        self.feedback = "Get ready!"

        self.is_calibrated = False
        self.calibration_start = None
        self.calibration_values = []

        self.last_rep_score = 100
        self.current_stats = {}
        self.rep_tempo_history = []
        self._last_voice_warn = 0.0

    def _result(self, counter=None, feedback=None, score=None, fatigue=None):
        return {
            "counter": self.state_machine.reps if counter is None else int(counter),
            "feedback": self.feedback if feedback is None else str(feedback),
            "form_score": int(self.last_rep_score if score is None else score),
            "stats_v2": self.current_stats,
            "fatigue_status": self.fatigue_analyzer.get_status() if fatigue is None else fatigue,
        }

    @staticmethod
    def _weighted(left_val, left_w, right_val, right_w):
        lw = max(float(left_w), 0.0)
        rw = max(float(right_w), 0.0)
        den = lw + rw + 1e-8
        return (left_val * lw + right_val * rw) / den

    def _build_error_list(self, feedback):
        if feedback in ("Good Form", "Strong Push!", "Hold... Push!"):
            return []
        return [{"msg": feedback}]

    def process(self, landmarks):
        now = time.time()
        try:
            if not landmarks or len(landmarks) <= self.R_ANKLE:
                self.feedback = "No landmarks"
                return self._result(score=0)

            l_vis = float(getattr(landmarks[self.L_SHOULDER], "visibility", 0.0))
            r_vis = float(getattr(landmarks[self.R_SHOULDER], "visibility", 0.0))
            confidence = max(l_vis, r_vis)

            if confidence < self.MIN_VIS:
                self.feedback = "Visibility low"
                return self._result()

            l_el_vis = float(getattr(landmarks[self.L_ELBOW], "visibility", 0.0))
            r_el_vis = float(getattr(landmarks[self.R_ELBOW], "visibility", 0.0))
            l_hi_vis = float(getattr(landmarks[self.L_HIP], "visibility", 0.0))
            r_hi_vis = float(getattr(landmarks[self.R_HIP], "visibility", 0.0))
            l_an_vis = float(getattr(landmarks[self.L_ANKLE], "visibility", 0.0))
            r_an_vis = float(getattr(landmarks[self.R_ANKLE], "visibility", 0.0))

            l_shoulder = [landmarks[self.L_SHOULDER].x, landmarks[self.L_SHOULDER].y]
            r_shoulder = [landmarks[self.R_SHOULDER].x, landmarks[self.R_SHOULDER].y]
            l_elbow = [landmarks[self.L_ELBOW].x, landmarks[self.L_ELBOW].y]
            r_elbow = [landmarks[self.R_ELBOW].x, landmarks[self.R_ELBOW].y]
            l_wrist = [landmarks[self.L_WRIST].x, landmarks[self.L_WRIST].y]
            r_wrist = [landmarks[self.R_WRIST].x, landmarks[self.R_WRIST].y]
            l_hip = [landmarks[self.L_HIP].x, landmarks[self.L_HIP].y]
            r_hip = [landmarks[self.R_HIP].x, landmarks[self.R_HIP].y]
            l_ankle = [landmarks[self.L_ANKLE].x, landmarks[self.L_ANKLE].y]
            r_ankle = [landmarks[self.R_ANKLE].x, landmarks[self.R_ANKLE].y]

            # 1) Biomechanics
            l_elbow_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)
            r_elbow_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)
            elbow_weight_l = min(l_vis, l_el_vis)
            elbow_weight_r = min(r_vis, r_el_vis)
            raw_elbow_angle = self._weighted(l_elbow_angle, elbow_weight_l, r_elbow_angle, elbow_weight_r)
            elbow_angle = float(self.elbow_filter.filter(raw_elbow_angle))

            l_body_angle = calculate_angle(l_shoulder, l_hip, l_ankle)
            r_body_angle = calculate_angle(r_shoulder, r_hip, r_ankle)
            body_weight_l = min(l_vis, l_hi_vis, l_an_vis)
            body_weight_r = min(r_vis, r_hi_vis, r_an_vis)
            body_angle = float(self._weighted(l_body_angle, body_weight_l, r_body_angle, body_weight_r))

            # 2) Calibration
            if not self.is_calibrated:
                if self.calibration_start is None:
                    self.calibration_start = now

                # Collect stable plank-like values only.
                if 130 <= body_angle <= 210:
                    self.calibration_values.append(body_angle)

                if (now - self.calibration_start) < self.CALIBRATION_SECONDS or len(self.calibration_values) < self.CALIBRATION_MIN_SAMPLES:
                    self.current_stats = {
                        "mode": "Pushup",
                        "state": PushupState.REST,
                        "score": 100,
                        "rep_count": 0,
                        "angle": 180.0,
                        "elbow_angle": 180.0,
                        "stability": 0.0,
                        "plank_deviation": 0.0,
                        "visibility": confidence,
                        "error_count": 0,
                        "hold_time": 0.0,
                        "errors": [],
                    }
                    self.feedback = "Calibrating plank..."
                    return self._result(counter=0, feedback=self.feedback, score=100, fatigue="OPTIMAL")

                self.plank_tracker.update(float(np.median(self.calibration_values)))
                self.is_calibrated = True
                speak("Plank calibrated. Start pushing", category="system")

            # 3) Stability
            stability_variance = float(self.stability_tracker.update(elbow_angle))

            # Adapt plank baseline slowly while in top phase.
            if self.state_machine.state == PushupState.REST and elbow_angle > 150:
                self.plank_tracker.update(body_angle)

            # 4) State machine
            state, changed = self.state_machine.update(elbow_angle, stability_variance)

            # 5) Timing and rep boundaries
            if changed and state == PushupState.DESCENDING:
                self.rep_start_time = now
                self.scoring_engine.reset_rep_metrics()

            current_rep_tempo = None
            if state != PushupState.REST and self.rep_start_time is not None:
                current_rep_tempo = now - self.rep_start_time

            # 6) Scoring
            plank_base = self.plank_tracker.get()
            if plank_base is None:
                plank_base = body_angle
            plank_deviation = float(abs(body_angle - plank_base))

            score, _ = self.scoring_engine.process_frame(
                elbow_angle,
                elbow_angle,
                plank_deviation,
                stability_variance,
                state,
                current_rep_tempo,
            )
            score = int(np.clip(score, 0, 100))
            self.last_rep_score = score

            # 7) Rep completion validation
            rep_invalid = False
            if changed and state == PushupState.REST and self.state_machine.rep_counted:
                rep_time = 0.0 if self.rep_start_time is None else now - self.rep_start_time
                valid = True
                if self.state_machine.lowest_angle > self.DEPTH_GOOD_MAX:
                    valid = False
                if rep_time < self.MIN_REP_TIME:
                    valid = False
                if plank_deviation > 25:
                    valid = False

                if not valid:
                    self.state_machine.cancel_last_rep()
                    rep_invalid = True
                    self.feedback = "Rep invalid - fix depth/plank"
                else:
                    speak(f"Rep {self.state_machine.reps}", category="rep")
                    self.rep_tempo_history.append(rep_time)
                    if len(self.rep_tempo_history) > 20:
                        self.rep_tempo_history.pop(0)

                    self.session_logger.log_rep({
                        "max_angle": 180.0,
                        "hold_duration": 0.0,
                        "lift_time": float(rep_time * 0.5),
                        "lower_time": float(rep_time * 0.5),
                        "avg_stability": stability_variance,
                        "visibility_score": confidence,
                        "error_count": 0,
                        "final_score": score,
                    })

                self.rep_start_time = None

            # 8) Feedback priority
            if not rep_invalid:
                if plank_deviation > 15:
                    self.feedback = "Fix plank alignment"
                elif state != PushupState.REST and self.state_machine.lowest_angle > 110:
                    self.feedback = "Go lower"
                elif state == PushupState.BOTTOM:
                    self.feedback = "Hold... then push"
                elif state == PushupState.ASCENDING:
                    self.feedback = "Strong push"
                else:
                    self.feedback = "Good Form"

            # Optional voice warnings with cooldown.
            if now - self._last_voice_warn > 2.5:
                if plank_deviation > 18:
                    speak("Keep hips steady", category="form")
                    self._last_voice_warn = now
                elif state != PushupState.REST and self.state_machine.lowest_angle > 112:
                    speak("Go deeper", category="form")
                    self._last_voice_warn = now

            fatigue_status = self.fatigue_analyzer.update(elbow_angle, stability_variance, plank_deviation)

            errors = self._build_error_list(self.feedback)
            self.current_stats = {
                "mode": "Pushup",
                "state": state,
                "score": score,
                "feedback": self.feedback,
                "rep_count": int(self.state_machine.reps),
                "angle": round(elbow_angle, 2),
                "elbow_angle": round(elbow_angle, 2),
                "plank_deviation": round(plank_deviation, 2),
                "stability": round(stability_variance, 3),
                "visibility": round(confidence, 3),
                "error_count": len(errors),
                "hold_time": 0.0,
                "errors": errors,
            }

            return {
                "counter": self.state_machine.reps,
                "feedback": self.feedback,
                "form_score": score,
                "stats_v2": self.current_stats,
                "fatigue_status": fatigue_status,
            }

        except Exception as exc:
            self.feedback = f"Error: {exc}"
            return self._result(score=0)

    def render_overlay(self, frame, results):
        return self.ui_renderer.render(
            frame,
            self.current_stats,
            results.get("session_stats", {}),
            results.get("fatigue_status", "OPTIMAL"),
        )

    def get_summary(self):
        stats = self.session_logger.get_session_stats()
        avg_tempo = float(np.mean(self.rep_tempo_history)) if self.rep_tempo_history else 0.0
        fatigue = self.fatigue_analyzer.get_status()
        return {
            "total_reps": int(self.state_machine.reps),
            "avg_score": float(stats.get("avg_score", 0.0)),
            "best_rep": float(stats.get("best_rep", 0.0)),
            "avg_tempo": round(avg_tempo, 2),
            "fatigue": fatigue,
        }
