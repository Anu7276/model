"""
Stable and accurate squat coach for real-time use.

Design goals:
- robust rep counting with hysteresis and frame confirmation
- adaptive calibration and depth targets
- bilateral quality checks (symmetry, knee tracking, lean)
- practical fatigue signal for live UI
"""

import time
import numpy as np

from core.angle_engine import calculate_angle, JitterFilter, DynamicBaselineTracker
from core.stability_tracker import StabilityTracker
from core.session_logger import SessionLogger
from core.fatigue_analyzer import FatigueAnalyzer
from ui.overlay_renderer import OverlayRenderer
from voice import speak


class SquatV2Coach:
    MIN_VIS = 0.20
    CALIBRATION_SECONDS = 2.0
    UP = "UP"
    DOWN = "DOWN"

    def __init__(self):
        # Core engines
        self.stability_tracker = StabilityTracker(size=20)
        self.session_logger = SessionLogger()
        self.fatigue_analyzer = FatigueAnalyzer()
        self.ui_renderer = OverlayRenderer()

        # Signal filters
        self.l_knee_filter = JitterFilter(alpha=0.14)
        self.r_knee_filter = JitterFilter(alpha=0.14)
        self.knee_filter = JitterFilter(alpha=0.10)
        self.lean_filter = JitterFilter(alpha=0.18)

        # Personalized baselines
        self.standing_tracker = DynamicBaselineTracker(alpha=0.08)
        self.depth_tracker = DynamicBaselineTracker(alpha=0.20)

        # Session state
        self.counter = 0
        self.state = self.UP
        self.feedback = "Stand straight for calibration"
        self.last_score = 100

        # Calibration
        self.is_calibrated = False
        self.calibration_start = None
        self.calibration_values = []

        # Rep tracking
        self.rep_start_time = None
        self.lowest_knee_this_rep = 180.0
        self.down_frames = 0
        self.enter_down_confirm_frames = 2
        self.exit_up_confirm_frames = 2
        self._up_candidate_frames = 0
        self.frame_issues = {"valgus": 0, "lean": 0, "depth": 0, "symmetry": 0}

        # History
        self.rep_durations = []
        self.depth_history = []
        self.score_history = []

        # Voice throttle for warnings
        self._last_warn_at = 0.0
        self.current_stats = {}

    def _safe_xy_vis(self, landmarks, idx):
        lm = landmarks[idx]
        return [lm.x, lm.y], float(getattr(lm, "visibility", 0.0))

    def _weighted(self, left_val, left_vis, right_val, right_vis):
        left_w = max(left_vis, 0.0)
        right_w = max(right_vis, 0.0)
        den = left_w + right_w + 1e-8
        return (left_val * left_w + right_val * right_w) / den

    def _calibration_response(self):
        self.current_stats = {
            "mode": "Squat",
            "state": self.state,
            "stability": 0.0,
            "angle": 180.0,
            "elbow_angle": 180.0,
            "depth_target": 100.0,
            "rep_count": int(self.counter),
            "score": 100,
            "feedback": "Calibrating... stand tall and still",
            "error_count": 0,
            "hold_time": 0.0,
            "visibility": 1.0,
            "errors": [],
        }
        return {
            "counter": self.counter,
            "feedback": "Calibrating... stand tall and still",
            "form_score": 100,
            "stats_v2": self.current_stats,
            "fatigue_status": "OPTIMAL",
        }

    def _get_depth_target(self):
        # Lower angle means deeper squat.
        if len(self.depth_history) >= 4:
            target = float(np.percentile(self.depth_history[-20:], 25))
            return float(np.clip(target, 88.0, 108.0))

        standing_base = self.standing_tracker.get() or 170.0
        # Default target roughly 40-45 deg below standing angle.
        return float(np.clip(standing_base - 42.0, 92.0, 110.0))

    def _score_rep(self, lowest_angle, symmetry, valgus_ratio, lean_ratio, stability, duration):
        score = 100.0
        depth_target = self._get_depth_target()

        # Depth
        depth_error = max(0.0, lowest_angle - depth_target)
        score -= min(35.0, depth_error * 1.0)

        # Symmetry
        if symmetry > 16:
            score -= 15
        elif symmetry > 10:
            score -= 7

        # Knee collapse
        if valgus_ratio < 0.58:
            score -= 18
        elif valgus_ratio < 0.70:
            score -= 10

        # Torso lean
        if lean_ratio > 0.28:
            score -= 16
        elif lean_ratio > 0.18:
            score -= 8

        # Stability
        if stability > 14:
            score -= 12
        elif stability > 9:
            score -= 6

        # Tempo
        if duration < 0.8:
            score -= 12
        elif duration > 7.0:
            score -= 8

        return int(np.clip(score, 0, 100))

    def _fatigue_status(self, frame_fatigue):
        if len(self.rep_durations) < 4:
            return "FATIGUED" if frame_fatigue == "FATIGUED" else "OPTIMAL"

        early_list = list(self.rep_durations)[:2]
        recent_list = list(self.rep_durations)[-2:]
        early = sum(early_list) / len(early_list) if early_list else 1.0
        recent = sum(recent_list) / len(recent_list) if recent_list else 1.0
        ratio = float(recent) / (float(early) + 1e-8)

        if ratio >= 1.6:
            return "HIGH"
        if ratio >= 1.3:
            return "MODERATE"
        return "FATIGUED" if frame_fatigue == "FATIGUED" else "OPTIMAL"

    def _feedback(self, knee_angle, symmetry, valgus_ratio, lean_ratio):
        target = self._get_depth_target()

        if self.state == self.DOWN:
            if valgus_ratio < 0.65:
                return "Knees caving in - push knees out"
            if lean_ratio > 0.22:
                return "Chest up - avoid forward lean"
            if knee_angle > target + 12:
                return "Go deeper"
            if symmetry > 14:
                return "Balance both legs"
            return "Great depth - drive up"

        if knee_angle < target + 15:
            return "Drive up and lock hips"
        return "Stable stance - squat down"

    def process(self, landmarks):
        now = time.time()

        try:
            if not landmarks or len(landmarks) < 17:
                self.current_stats = {
                    "mode": "Squat",
                    "state": self.state,
                    "stability": 0.0,
                    "angle": 180.0,
                    "elbow_angle": 180.0,
                    "rep_count": int(self.counter),
                    "score": int(self.last_score),
                    "feedback": "No landmarks detected",
                    "error_count": 1,
                    "hold_time": 0.0,
                    "visibility": 0.0,
                    "errors": [{"msg": "No landmarks detected"}],
                }
                return {
                    "counter": self.counter,
                    "feedback": "No landmarks detected",
                    "form_score": self.last_score,
                    "stats_v2": self.current_stats,
                    "fatigue_status": "OPTIMAL",
                }

            # Landmarks
            l_sh, l_sh_vis = self._safe_xy_vis(landmarks, 5)
            r_sh, r_sh_vis = self._safe_xy_vis(landmarks, 6)
            l_hi, l_hi_vis = self._safe_xy_vis(landmarks, 11)
            r_hi, r_hi_vis = self._safe_xy_vis(landmarks, 12)
            l_kn, l_kn_vis = self._safe_xy_vis(landmarks, 13)
            r_kn, r_kn_vis = self._safe_xy_vis(landmarks, 14)
            l_an, l_an_vis = self._safe_xy_vis(landmarks, 15)
            r_an, r_an_vis = self._safe_xy_vis(landmarks, 16)

            vis_gate = float(max(l_kn_vis, r_kn_vis, l_hi_vis, r_hi_vis))
            if vis_gate < self.MIN_VIS:
                self.current_stats = {
                    "mode": "Squat",
                    "state": self.state,
                    "stability": 0.0,
                    "angle": 180.0,
                    "elbow_angle": 180.0,
                    "rep_count": int(self.counter),
                    "score": int(self.last_score),
                    "feedback": "Visibility low - move into frame",
                    "error_count": 1,
                    "hold_time": 0.0,
                    "visibility": float(vis_gate),
                    "errors": [{"msg": "Visibility low - move into frame"}],
                }
                return {
                    "counter": self.counter,
                    "feedback": "Visibility low - move into frame",
                    "form_score": self.last_score,
                    "stats_v2": self.current_stats,
                    "fatigue_status": "OPTIMAL",
                }

            # Biomechanics
            l_knee_raw = calculate_angle(l_hi, l_kn, l_an)
            r_knee_raw = calculate_angle(r_hi, r_kn, r_an)
            l_knee = self.l_knee_filter.filter(l_knee_raw)
            r_knee = self.r_knee_filter.filter(r_knee_raw)

            combined_knee = self._weighted(l_knee, l_kn_vis, r_knee, r_kn_vis)
            knee_angle = self.knee_filter.filter(combined_knee)
            symmetry = float(abs(l_knee - r_knee))

            # Biomechanical Normalization
            hip_euclidean = float(np.linalg.norm(np.array(l_hi) - np.array(r_hi))) + 1e-6
            knee_euclidean = float(np.linalg.norm(np.array(l_kn) - np.array(r_kn)))
            valgus_ratio = knee_euclidean / hip_euclidean

            # Lean ratio normalized by torso length (Mid-Shoulder to Mid-Hip)
            mid_sh = np.array([(l_sh[0] + r_sh[0]) * 0.5, (l_sh[1] + r_sh[1]) * 0.5])
            mid_hi = np.array([(l_hi[0] + r_hi[0]) * 0.5, (l_hi[1] + r_hi[1]) * 0.5])
            torso_len = float(np.linalg.norm(mid_sh - mid_hi)) + 1e-6
            
            mid_sh_x = mid_sh[0]
            mid_hi_x = mid_hi[0]
            lean_ratio = self.lean_filter.filter(abs(mid_sh_x - mid_hi_x) / torso_len)

            stability_variance = float(self.stability_tracker.update(knee_angle))

            # Calibration
            if not self.is_calibrated:
                if self.calibration_start is None:
                    self.calibration_start = now
                    speak("Stand straight for calibration", category="system")

                # keep only near-standing values during calibration
                if knee_angle > 145:
                    self.calibration_values.append(knee_angle)

                if now - self.calibration_start < 3.0 or len(self.calibration_values) < 12:
                    return self._calibration_response()

                stand = float(np.median(self.calibration_values))
                self.standing_tracker.update(stand)
                self.is_calibrated = True
                speak("Calibration done. Start squats", category="system")

            standing_base = self.standing_tracker.get() or 170.0
            down_threshold = float(np.clip(standing_base - 24.0, 130.0, 160.0))
            up_threshold = float(np.clip(standing_base - 10.0, down_threshold + 8.0, 172.0))

            # Adapt standing baseline only when clearly upright
            if self.state == self.UP and knee_angle > up_threshold + 5.0:
                self.standing_tracker.update(knee_angle)

            # State machine
            if self.state == self.UP:
                if knee_angle < down_threshold:
                    self.down_frames += 1
                else:
                    self.down_frames = 0

                if self.down_frames >= self.enter_down_confirm_frames:
                    self.state = self.DOWN
                    self.rep_start_time = now
                    self.lowest_knee_this_rep = knee_angle
                    self._up_candidate_frames = 0
                    self.frame_issues = {"valgus": 0, "lean": 0, "depth": 0, "symmetry": 0}

            else:  # DOWN
                self.lowest_knee_this_rep = min(self.lowest_knee_this_rep, knee_angle)

                if valgus_ratio < 0.67:
                    self.frame_issues["valgus"] += 1
                if lean_ratio > 0.20:
                    self.frame_issues["lean"] += 1
                if symmetry > 14:
                    self.frame_issues["symmetry"] += 1
                if knee_angle > self._get_depth_target() + 12:
                    self.frame_issues["depth"] += 1

                if knee_angle > up_threshold:
                    self._up_candidate_frames += 1
                else:
                    self._up_candidate_frames = 0

                rep_duration = now - (self.rep_start_time or now)

                # Abort very long unresolved descent
                if rep_duration > 10.0:
                    self.state = self.UP
                    self.rep_start_time = None
                    self.down_frames = 0
                    self._up_candidate_frames = 0

                if self._up_candidate_frames >= self.exit_up_confirm_frames:
                    valid_rep = (rep_duration >= 0.8) and (self.lowest_knee_this_rep <= self._get_depth_target() + 18)

                    if valid_rep:
                        self.counter += 1

                        self.last_score = self._score_rep(
                            lowest_angle=self.lowest_knee_this_rep,
                            symmetry=symmetry,
                            valgus_ratio=valgus_ratio,
                            lean_ratio=lean_ratio,
                            stability=stability_variance,
                            duration=rep_duration,
                        )
                        self.score_history.append(self.last_score)
                        self.depth_history.append(self.lowest_knee_this_rep)
                        self.rep_durations.append(rep_duration)

                        self.depth_history = self.depth_history[-25:]
                        self.rep_durations = self.rep_durations[-25:]
                        self.score_history = self.score_history[-25:]

                        self.depth_tracker.update(self.lowest_knee_this_rep)

                        self.session_logger.log_rep({
                            "max_angle": float(standing_base),
                            "hold_duration": 0.0,
                            "lift_time": float(rep_duration * 0.5),
                            "lower_time": float(rep_duration * 0.5),
                            "avg_stability": float(stability_variance),
                            "visibility_score": float(vis_gate),
                            "error_count": int(sum(self.frame_issues.values())),
                            "final_score": float(self.last_score),
                        })

                        speak(f"Rep {self.counter}", category="rep")
                        if self.counter in (5, 10, 15, 20, 25, 30):
                            speak(f"{self.counter} reps, keep going", category="milestone")
                    else:
                        # only occasional warning for rejected reps
                        if now - self._last_warn_at > 2.2:
                            if rep_duration < 0.8:
                                speak("Too fast. Control the squat", category="warning")
                            else:
                                speak("Go deeper for full rep", category="form")
                            self._last_warn_at = now

                    self.state = self.UP
                    self.rep_start_time = None
                    self.down_frames = 0
                    self._up_candidate_frames = 0

            # Fatigue and feedback
            frame_fatigue = self.fatigue_analyzer.update(knee_angle, stability_variance, lean_ratio * 100.0)
            fatigue_status = self._fatigue_status(frame_fatigue)
            self.feedback = self._feedback(knee_angle, symmetry, valgus_ratio, lean_ratio)

            # Controlled warning voice to avoid spam
            if self.state == self.DOWN and now - self._last_warn_at > 2.6:
                if valgus_ratio < 0.62:
                    speak("Push knees out", category="form")
                    self._last_warn_at = now
                elif lean_ratio > 0.24:
                    speak("Chest up", category="form")
                    self._last_warn_at = now

            errors = [] if self.feedback.startswith("Stable") or self.feedback.startswith("Great") else [{"msg": self.feedback}]
            stats_v2 = {
                "mode": "Squat",
                "state": self.state,
                "stability": float(int(float(stability_variance) * 1000) / 1000.0),
                "angle": float(int(float(knee_angle) * 100) / 100.0),
                "elbow_angle": float(int(float(knee_angle) * 100) / 100.0),
                "symmetry": float(int(float(symmetry) * 100) / 100.0),
                "valgus_ratio": float(int(float(valgus_ratio) * 1000) / 1000.0),
                "lean": float(int(float(lean_ratio) * 1000) / 1000.0),
                "depth_target": float(int(float(self._get_depth_target()) * 10) / 10.0),
                "down_threshold": float(int(float(down_threshold) * 10) / 10.0),
                "up_threshold": float(int(float(up_threshold) * 10) / 10.0),
                "rep_count": int(self.counter),
                "score": int(self.last_score),
                "feedback": self.feedback,
                "error_count": len(errors),
                "hold_time": 0.0,
                "visibility": float(int(float(vis_gate) * 1000) / 1000.0),
                "errors": errors,
            }
            self.current_stats = stats_v2

            return {
                "counter": self.counter,
                "feedback": self.feedback,
                "form_score": int(self.last_score),
                "stats_v2": stats_v2,
                "fatigue_status": fatigue_status,
            }

        except Exception as exc:
            self.current_stats = {
                "mode": "Squat",
                "state": self.state,
                "stability": 0.0,
                "angle": 0.0,
                "elbow_angle": 0.0,
                "rep_count": int(self.counter),
                "score": int(self.last_score),
                "feedback": f"Error: {exc}",
                "error_count": 1,
                "hold_time": 0.0,
                "visibility": 0.0,
                "errors": [{"msg": f"Error: {exc}"}],
            }
            return {
                "counter": self.counter,
                "feedback": f"Error: {exc}",
                "form_score": int(self.last_score),
                "stats_v2": self.current_stats,
                "fatigue_status": "OPTIMAL",
            }

    def get_summary(self):
        if not self.score_history:
            return {"total_reps": self.counter, "avg_score": 0.0, "best_depth": 0.0, "fatigue": "OPTIMAL"}

        return {
            "total_reps": self.counter,
            "avg_score": float(np.mean(self.score_history)),
            "best_depth": float(min(self.depth_history)) if self.depth_history else 0.0,
            "fatigue": self._fatigue_status(self.fatigue_analyzer.get_status()),
        }

    def render_overlay(self, frame, results):
        return self.ui_renderer.render(
            frame,
            results.get("stats_v2", self.current_stats),
            results.get("session_stats", {}),
            results.get("fatigue_status", "OPTIMAL"),
        )
