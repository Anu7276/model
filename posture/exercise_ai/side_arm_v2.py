"""side_arm_v2.py
Professional Side Weight Holding coach with stable calibration, bilateral checks, and strict rep validation.
"""

import time
import numpy as np

from core.angle_engine import calculate_horizontal_elevation, calculate_angle, calculate_torso_tilt
from core.state_machine import LateralRaiseStateMachine, LateralRaiseState
from core.stability_tracker import StabilityTracker
from core.scoring_engine import ScoringEngine
from core.fatigue_analyzer import FatigueAnalyzer
from core.session_logger import SessionLogger
from ui.overlay_renderer import OverlayRenderer
from voice import speak


class SideArmV2Coach:
    L_EAR = 7
    R_EAR = 8
    L_SHOULDER = 11
    R_SHOULDER = 12
    L_ELBOW = 13
    R_ELBOW = 14
    L_WRIST = 15
    R_WRIST = 16
    L_HIP = 23
    R_HIP = 24
    L_KNEE = 25
    R_KNEE = 26

    MIN_VIS = 0.45
    CALIBRATION_SECONDS = 3.0
    CALIBRATION_MIN_SAMPLES = 15
    LEAN_WARN = 16.0
    LEAN_DANGER = 24.0
    SYMMETRY_MIN_ANGLE = 65.0
    SYMMETRY_MAX_DIFF = 10.0
    MIN_ELBOW_VALID = 150.0
    MAX_LEAN_VALID = 18.0
    MIN_HOLD_VALID = 0.25

    def __init__(self):
        self.state_machine = LateralRaiseStateMachine()
        self.stability_tracker = StabilityTracker(size=15)
        self.scoring_engine = ScoringEngine(exercise_type="LATERAL_RAISE")
        self.fatigue_analyzer = FatigueAnalyzer()
        self.session_logger = SessionLogger()
        self.ui_renderer = OverlayRenderer()

        self.current_stats = {}
        self.last_visibility = 0.0

        self.is_calibrated = False
        self.calibration_start = None
        self.calibration_values = []
        self.baseline_angle = 15.0

        self.rep_start_time = None
        self.rep_stabilities = []
        self._last_voice_warn = 0.0

        self.angle_history = {"LEFT": [], "RIGHT": []}
        self.elbow_history = {"LEFT": [], "RIGHT": []}
        self.torso_history = {"LEFT": [], "RIGHT": []}
        self.elevation_history = {"LEFT": [], "RIGHT": []}

    def _smooth(self, history, value, size=5):
        history.append(float(value))
        if len(history) > size:
            history.pop(0)
        return float(sum(history) / len(history))

    def _result(self, feedback, score=None):
        return {
            "counter": int(self.state_machine.reps),
            "feedback": feedback,
            "form_score": int(self.scoring_engine.current_score if score is None else score),
            "stats_v2": self.current_stats,
            "fatigue_status": self.fatigue_analyzer.get_status(),
        }

    def _build_side_metrics(self, landmarks, side, s_idx, e_idx, w_idx, h_idx, k_idx, ear_idx):
        s_pt = [landmarks[s_idx].x, landmarks[s_idx].y]
        e_pt = [landmarks[e_idx].x, landmarks[e_idx].y]
        w_pt = [landmarks[w_idx].x, landmarks[w_idx].y]
        h_pt = [landmarks[h_idx].x, landmarks[h_idx].y]

        raw_angle = calculate_angle(h_pt, s_pt, e_pt)
        angle = self._smooth(self.angle_history[side], raw_angle)

        raw_elev = calculate_horizontal_elevation(s_pt, e_pt)
        elevation = self._smooth(self.elevation_history[side], raw_elev)

        raw_elbow = calculate_angle(s_pt, e_pt, w_pt)
        elbow_angle = self._smooth(self.elbow_history[side], raw_elbow)

        torso_tilt = calculate_torso_tilt(s_pt, h_pt)
        lean_deviation = self._smooth(self.torso_history[side], torso_tilt)

        shoulder_ear_dist = abs(landmarks[s_idx].y - landmarks[ear_idx].y)
        shrugging = shoulder_ear_dist < 0.04

        return {
            "angle": angle,
            "elevation": elevation,
            "elbow_angle": elbow_angle,
            "lean_deviation": lean_deviation,
            "shrugging": shrugging,
            "visibility": float(getattr(landmarks[s_idx], "visibility", 0.0)),
        }

    def process(self, landmarks):
        try:
            if not landmarks or len(landmarks) <= self.R_KNEE:
                return self._result("No landmarks", score=0)

            l_vis = float(getattr(landmarks[self.L_SHOULDER], "visibility", 0.0))
            r_vis = float(getattr(landmarks[self.R_SHOULDER], "visibility", 0.0))
            self.last_visibility = max(l_vis, r_vis)

            if self.last_visibility < self.MIN_VIS:
                return {
                    "counter": int(self.state_machine.reps),
                    "feedback": "Visibility low",
                    "form_score": int(self.scoring_engine.current_score),
                    "ui_skip": True,
                    "visibility": self.last_visibility,
                    "stats_v2": self.current_stats,
                    "fatigue_status": self.fatigue_analyzer.get_status(),
                }

            results = {
                "LEFT": self._build_side_metrics(
                    landmarks,
                    "LEFT",
                    self.L_SHOULDER,
                    self.L_ELBOW,
                    self.L_WRIST,
                    self.L_HIP,
                    self.L_KNEE,
                    self.L_EAR,
                ),
                "RIGHT": self._build_side_metrics(
                    landmarks,
                    "RIGHT",
                    self.R_SHOULDER,
                    self.R_ELBOW,
                    self.R_WRIST,
                    self.R_HIP,
                    self.R_KNEE,
                    self.R_EAR,
                ),
            }

            l_ang = results["LEFT"]["angle"]
            r_ang = results["RIGHT"]["angle"]

            if l_ang > r_ang + 15:
                main_side = "LEFT"
            elif r_ang > l_ang + 15:
                main_side = "RIGHT"
            else:
                main_side = "LEFT" if l_vis >= r_vis else "RIGHT"

            primary = results[main_side]

            now = time.time()
            if not self.is_calibrated:
                if self.calibration_start is None:
                    self.calibration_start = now

                if primary["angle"] < 50:
                    self.calibration_values.append(primary["angle"])

                if (now - self.calibration_start) < self.CALIBRATION_SECONDS or len(self.calibration_values) < self.CALIBRATION_MIN_SAMPLES:
                    self.current_stats = {
                        "mode": "Side Weight Holding",
                        "state": LateralRaiseState.REST,
                        "score": 100,
                        "rep_count": 0,
                        "angle": 0.0,
                        "elbow_angle": 180.0,
                        "stability": 0.0,
                        "visibility": self.last_visibility,
                        "error_count": 0,
                        "hold_time": 0.0,
                        "errors": [],
                    }
                    return {
                        "counter": 0,
                        "feedback": "Calibrating - hold weight by your side",
                        "form_score": 100,
                        "stats_v2": self.current_stats,
                        "fatigue_status": "OPTIMAL",
                    }

                self.baseline_angle = float(np.median(self.calibration_values))
                self.is_calibrated = True
                speak("Side weight holding calibration complete", category="system")

            adj_angle = max(0.0, primary["angle"] - self.baseline_angle)
            if adj_angle < 25:
                adj_angle = 0.0

            stability_variance = float(self.stability_tracker.update(adj_angle))
            state, changed = self.state_machine.update(adj_angle, stability_variance)

            if state == LateralRaiseState.LIFTING and adj_angle > 30 and self.rep_start_time is None:
                self.rep_start_time = now
                self.rep_stabilities = []

            self.rep_stabilities.append(stability_variance)
            if len(self.rep_stabilities) > 120:
                self.rep_stabilities.pop(0)

            feedback = "Perfect Form" if state == LateralRaiseState.HOLD else "Good Control"
            if primary["lean_deviation"] > self.LEAN_DANGER:
                feedback = "Danger: excessive lean"
            elif primary["lean_deviation"] > self.LEAN_WARN:
                feedback = "Avoid leaning"
            elif primary["shrugging"] and adj_angle > 70:
                feedback = "Relax shoulders"
            elif adj_angle > 110:
                feedback = "Arm too high"
            elif adj_angle < 70 and state == LateralRaiseState.LIFTING:
                feedback = "Lift higher"
            elif primary["elbow_angle"] < 155:
                feedback = "Straighten elbow"

            symmetry_err = False
            if results["LEFT"]["angle"] > self.SYMMETRY_MIN_ANGLE and results["RIGHT"]["angle"] > self.SYMMETRY_MIN_ANGLE:
                if abs(results["LEFT"]["angle"] - results["RIGHT"]["angle"]) > self.SYMMETRY_MAX_DIFF:
                    symmetry_err = True
                    if feedback in ("Perfect Form", "Good Control"):
                        feedback = "Asymmetrical lift"

            current_rep_tempo = None
            if changed and state == LateralRaiseState.REST and self.rep_start_time is not None:
                current_rep_tempo = now - self.rep_start_time
                self.rep_start_time = None

            score, _ = self.scoring_engine.process_frame(
                adj_angle,
                primary["elbow_angle"],
                primary["lean_deviation"],
                stability_variance,
                state,
                current_rep_tempo,
            )
            score = int(np.clip(score, 0, 100))

            rep_invalid = False
            if changed and state == LateralRaiseState.REST and self.state_machine.rep_counted:
                valid = True
                if self.scoring_engine.max_angle_in_rep < 85:
                    valid = False
                if self.state_machine.hold_duration < self.MIN_HOLD_VALID:
                    valid = False
                if current_rep_tempo and current_rep_tempo < 1.0:
                    valid = False
                if primary["elbow_angle"] < self.MIN_ELBOW_VALID:
                    valid = False
                if primary["lean_deviation"] > self.MAX_LEAN_VALID:
                    valid = False
                if symmetry_err:
                    valid = False

                if not valid:
                    self.state_machine.cancel_last_rep()
                    feedback = "Rep invalid - check form"
                    rep_invalid = True
                else:
                    speak(f"Rep {self.state_machine.reps}", category="rep")
                    avg_rep_stability = float(np.mean(self.rep_stabilities[-30:])) if self.rep_stabilities else 0.0
                    self.session_logger.log_rep({
                        "max_angle": float(self.scoring_engine.max_angle_in_rep),
                        "hold_duration": float(self.state_machine.hold_duration),
                        "lift_time": float(current_rep_tempo or 0.0),
                        "lower_time": 0.0,
                        "avg_stability": avg_rep_stability,
                        "visibility_score": float(self.last_visibility),
                        "error_count": int(symmetry_err) + int(primary["shrugging"]),
                        "final_score": float(score),
                    })

                self.scoring_engine.reset_rep_metrics()

            if now - self._last_voice_warn > 2.5:
                if primary["lean_deviation"] > 18:
                    speak("Keep torso upright", category="form")
                    self._last_voice_warn = now
                elif primary["elbow_angle"] < 150 and adj_angle > 40:
                    speak("Keep elbow straight", category="form")
                    self._last_voice_warn = now

            fatigue_status = self.fatigue_analyzer.update(adj_angle, stability_variance, primary["lean_deviation"])

            if rep_invalid:
                score = max(0, score - 10)

            errors = [] if feedback in ("Perfect Form", "Good Control") else [{"msg": feedback}]
            self.current_stats = {
                "mode": "Side Weight Holding",
                "state": state,
                "score": score,
                "feedback": feedback,
                "rep_count": int(self.state_machine.reps),
                "primary_side": main_side,
                "angle": round(adj_angle, 2),
                "primary_angle": round(adj_angle, 2),
                "raw_angle": round(primary["angle"], 2),
                "elevation": round(primary["elevation"], 2),
                "elbow_angle": round(primary["elbow_angle"], 2),
                "lean": round(primary["lean_deviation"], 2),
                "shrugging": bool(primary["shrugging"]),
                "symmetry_error": bool(symmetry_err),
                "stability": round(stability_variance, 3),
                "baseline": round(self.baseline_angle, 2),
                "visibility": round(self.last_visibility, 3),
                "hold_time": round(float(self.state_machine.hold_duration), 2),
                "error_count": len(errors),
                "errors": errors,
            }

            return {
                "counter": int(self.state_machine.reps),
                "feedback": feedback,
                "form_score": score,
                "stats_v2": self.current_stats,
                "fatigue_status": fatigue_status,
            }

        except Exception as exc:
            return self._result(f"Error: {exc}", score=0)

    def render_overlay(self, frame, results):
        if results.get("ui_skip") and self.last_visibility < 0.6:
            try:
                import cv2
                h, w, _ = frame.shape
                cv2.rectangle(frame, (w // 2 - 200, h // 2 - 50), (w // 2 + 200, h // 2 + 50), (0, 0, 255), -1)
                cv2.putText(frame, "VISIBILITY LOW", (w // 2 - 100, h // 2 + 10), 0, 0.8, (255, 255, 255), 2)
                return frame
            except Exception:
                return frame

        return self.ui_renderer.render(
            frame,
            results.get("stats_v2", self.current_stats),
            results.get("session_stats", {}),
            results.get("fatigue_status", "OPTIMAL"),
        )

    def get_summary(self):
        stats = self.session_logger.get_session_stats()
        return {
            "total_reps": int(self.state_machine.reps),
            "avg_score": float(stats.get("avg_score", 0.0)),
            "best_rep": float(stats.get("best_rep", 0.0)),
            "fatigue": self.fatigue_analyzer.get_status(),
        }
