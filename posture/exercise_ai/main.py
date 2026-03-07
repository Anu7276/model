"""
main.py — AI Exercise Coach Engine
Improvements:
 - Voice command control (start/stop/select/mute/score/reset)
 - MoveNet primary + MediaPipe fallback
 - Session summary on stop
 - Thread-safe frame pipeline
 - Beep on rep count (cross-platform)
 - Clean shutdown
"""

import cv2
import numpy as np
import time
import threading
import platform

from squat_v2   import SquatV2Coach
from pushup_v2  import PushupV2Coach
from side_arm_v2 import SideArmV2Coach
from voice      import (speak_system, speak_form, speak_warning,
                        start_listening, stop_listening, set_enabled,
                        speak)

# ── Cross-platform beep ───────────────────────────────────────────────────────
def _beep():
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(880, 120)
        else:
            # macOS / Linux — use cv2 or print bell
            print("\a", end="", flush=True)
    except Exception:
        pass


# ── Landmark adapter: MoveNet → duck-typed objects ───────────────────────────
class _Lm:
    __slots__ = ("x", "y", "visibility")
    def __init__(self, y, x, score):
        self.x, self.y, self.visibility = float(x), float(y), float(score)


# ── MoveNet body-part index → MediaPipe index mapping ────────────────────────
# MoveNet 17 keypoints (COCO order):
#  0:nose 1:l_eye 2:r_eye 3:l_ear 4:r_ear
#  5:l_sh 6:r_sh 7:l_el 8:r_el 9:l_wr 10:r_wr
# 11:l_hi 12:r_hi 13:l_kn 14:r_kn 15:l_an 16:r_an
#
# MediaPipe pose indices we need:
#  7:l_ear 8:r_ear 11:l_sh 12:r_sh 13:l_el 14:r_el
# 15:l_wr 16:r_wr 23:l_hi 24:r_hi 25:l_kn 26:r_kn 27:l_an 28:r_an
_MN2MP = {
    7:  3,   # l_ear
    8:  4,   # r_ear
    11: 5,   # l_sh
    12: 6,   # r_sh
    13: 7,   # l_el
    14: 8,   # r_el
    15: 9,   # l_wr
    16: 10,  # r_wr
    23: 11,  # l_hi
    24: 12,  # r_hi
    25: 13,  # l_kn
    26: 14,  # r_kn
    27: 15,  # l_an
    28: 16,  # r_an
}

def _to_mp_landmarks(kps):
    """Convert MoveNet 17-kp array to a 33-slot list indexed like MediaPipe."""
    result = [_Lm(0, 0, 0)] * 33
    for mp_idx, mn_idx in _MN2MP.items():
        y, x, score = kps[mn_idx]
        result[mp_idx] = _Lm(y, x, score)
    return result


# ── Exercise Engine ───────────────────────────────────────────────────────────

class ExerciseEngine:
    EXERCISES = ("squat", "pushup", "sidearm")

    def __init__(self, exercise_type: str, voice_commands: bool = True):
        self.exercise_type = exercise_type
        self._build_coach(exercise_type)

        # Load MoveNet
        self._model = None
        self._mp_pose = None
        self._init_model()

        # Camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS,          30)

        # State
        self.running      = True
        self.paused       = False
        self.last_frame   = None
        self.last_count   = 0
        self.score_hist   = []
        self.start_time   = time.time()
        self.last_stats   = {
            "counter": 0, "feedback": "Initializing…",
            "form_score": 100, "elapsed_time": 0,
            "avg_score": 100, "correct": 0, "incorrect": 0,
        }

        self._lock  = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        # Voice commands
        if voice_commands:
            ok = start_listening(self._on_voice_cmd)
            if ok:
                speak_system("Voice commands active. Say start, stop, or select an exercise.")

    # ── Coach factory ─────────────────────────────────────────────────────────

    def _build_coach(self, ex: str):
        if ex == "squat":
            self.coach = SquatV2Coach()
        elif ex == "pushup":
            self.coach = PushupV2Coach()
        else:
            self.coach = SideArmV2Coach()
        self.exercise_type = ex

    # ── Model init ────────────────────────────────────────────────────────────

    def _init_model(self):
        try:
            import tensorflow as tf
            import tensorflow_hub as hub
            print("[Engine] Loading MoveNet Lightning…")
            module = hub.load("https://tfhub.dev/google/movenet/singlepose/lightning/4")
            self._model = module.signatures["serving_default"]
            print("[Engine] MoveNet ready.")
        except Exception as e:
            print(f"[Engine] MoveNet failed ({e}) — falling back to MediaPipe.")
            self._init_mediapipe()

    def _init_mediapipe(self):
        try:
            import mediapipe as mp
            self._mp_pose = mp.solutions.pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=1,
            )
            print("[Engine] MediaPipe Pose ready.")
        except Exception as e:
            print(f"[Engine] MediaPipe also failed: {e}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def _infer_movenet(self, frame):
        import tensorflow as tf
        img = cv2.resize(frame, (192, 192))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        inp = tf.cast(tf.expand_dims(img, 0), tf.int32)
        out = self._model(inp)["output_0"].numpy()[0, 0]   # [17, 3]
        return _to_mp_landmarks(out)

    def _infer_mediapipe(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mp_pose.process(rgb)
        if res.pose_landmarks:
            return res.pose_landmarks.landmark
        return None

    def _get_landmarks(self, frame):
        if self._model:
            return self._infer_movenet(frame)
        if self._mp_pose:
            return self._infer_mediapipe(frame)
        return None

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            stats = self.last_stats.copy()
            stats["elapsed_time"] = int(time.time() - self.start_time)

            if not self.paused:
                lms = self._get_landmarks(frame)
                if lms:
                    result = self.coach.process(lms)
                    stats.update(result)

                    # Avg score
                    self.score_hist.append(result.get("form_score", 100))
                    if len(self.score_hist) > 300:
                        self.score_hist.pop(0)
                    stats["avg_score"] = int(sum(self.score_hist) / len(self.score_hist))

                    # Rep beep
                    cnt = result.get("counter", 0)
                    if cnt > self.last_count:
                        self.last_count = cnt
                        threading.Thread(target=_beep, daemon=True).start()

                    # Draw skeleton
                    self._draw_skeleton(frame, lms)

            with self._lock:
                self.last_frame = frame.copy()
                self.last_stats = stats

            time.sleep(0.001)

    # ── Skeleton overlay ──────────────────────────────────────────────────────

    _CONNECTIONS = [
        (11,13),(13,15),(12,14),(14,16),    # arms
        (11,12),(23,24),(11,23),(12,24),    # torso
        (23,25),(25,27),(24,26),(26,28),    # legs
    ]

    def _draw_skeleton(self, frame, lms):
        h, w = frame.shape[:2]
        for a, b in self._CONNECTIONS:
            try:
                la, lb = lms[a], lms[b]
                if la.visibility > 0.4 and lb.visibility > 0.4:
                    pa = (int(la.x * w), int(la.y * h))
                    pb = (int(lb.x * w), int(lb.y * h))
                    cv2.line(frame, pa, pb, (0, 200, 255), 2, cv2.LINE_AA)
            except Exception:
                pass
        for idx in range(29):
            try:
                lm = lms[idx]
                if lm.visibility > 0.4:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 180), -1, cv2.LINE_AA)
            except Exception:
                pass

    # ── Voice command handler ─────────────────────────────────────────────────

    def _on_voice_cmd(self, cmd: str):
        print(f"[VoiceCmd] {cmd}")
        if cmd == "stop":
            self.running = False
            speak_system("Stopping workout.")
        elif cmd == "pause":
            self.paused = True
            speak_system("Paused.")
        elif cmd == "resume":
            self.paused = False
            speak_system("Resuming.")
        elif cmd == "mute":
            set_enabled(False)
            print("[Voice] Muted.")
        elif cmd == "unmute":
            set_enabled(True)
            speak_system("Voice on.")
        elif cmd in ("pushup", "squat", "sidearm"):
            self._build_coach(cmd)
            self.last_count = 0
            self.score_hist = []
            self.start_time = time.time()
            display = "side weight holding" if cmd == "sidearm" else cmd
            speak_system(f"Switching to {display}.")
        elif cmd == "score":
            s = self.last_stats.get("form_score", 0)
            speak(f"Your current form score is {s} percent.")
        elif cmd == "reps":
            c = self.last_stats.get("counter", 0)
            speak(f"You have completed {c} reps.")
        elif cmd == "reset":
            self._build_coach(self.exercise_type)
            self.last_count = 0
            self.score_hist = []
            self.start_time = time.time()
            speak_system("Session reset.")

    # ── Public API ────────────────────────────────────────────────────────────

    def get_frame(self):
        with self._lock:
            return self.last_frame, self.last_stats.copy()

    def switch_exercise(self, ex: str):
        self._on_voice_cmd(ex)

    def get_session_summary(self):
        if hasattr(self.coach, "get_summary"):
            return self.coach.get_summary()
        return {}

    def release(self):
        self.running = False
        stop_listening()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.cap.release()
        if self._mp_pose:
            self._mp_pose.close()


# ── Minimal CLI runner ────────────────────────────────────────────────────────

def draw_hud(frame, stats, ex_name):
    cv2.rectangle(frame, (0, 0), (260, 380), (0, 0, 0), -1)
    f = cv2.FONT_HERSHEY_SIMPLEX
    w = (255, 255, 255)
    c = (0, 255, 255)
    cv2.putText(frame, ex_name.upper(),         (10, 40),  f, 0.9, c, 2)
    cv2.putText(frame, f"Reps: {stats['counter']}",        (10, 90),  f, 1.2, w, 2)
    score = stats['form_score']
    col = (0,255,0) if score > 80 else (0,165,255) if score > 50 else (0,0,255)
    cv2.putText(frame, f"Score: {score}%",      (10, 140), f, 1.0, col, 2)
    cv2.putText(frame, stats['feedback'][:22],  (10, 185), f, 0.55, w, 1)
    t = stats['elapsed_time']
    cv2.putText(frame, f"{t//60:02d}:{t%60:02d}", (10, 230), f, 0.8, c, 2)
    avg = stats.get('avg_score', 100)
    cv2.putText(frame, f"Avg: {int(avg)}%",     (10, 270), f, 0.65, (180,180,180), 1)
    cv2.putText(frame, "Q=quit  P=pause",        (10, 360), f, 0.45, (80,80,80), 1)


def main():
    print("Available: squat | pushup | sidearm (Side Weight Holding)")
    choice = input("Select exercise: ").strip().lower()
    if choice not in ("squat", "pushup", "sidearm"):
        choice = "squat"

    engine = ExerciseEngine(choice, voice_commands=True)
    speak_system(f"{choice} session started. Say stop to end.")

    while engine.running:
        frame, stats = engine.get_frame()
        if frame is None:
            time.sleep(0.03)
            continue

        draw_hud(frame, stats, choice)
        cv2.imshow("AI Exercise Coach", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("p"):
            engine.paused = not engine.paused
            speak_system("Paused." if engine.paused else "Resuming.")

    summary = engine.get_session_summary()
    print("\n=== Session Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    engine.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
