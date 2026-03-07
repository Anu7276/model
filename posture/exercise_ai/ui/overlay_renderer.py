try:
    import cv2
except Exception:
    cv2 = None

import numpy as np

class OverlayRenderer:
    def __init__(self):
        self.enabled = cv2 is not None
        if not self.enabled:
            return

        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_small = 0.5
        self.font_scale_med = 0.7
        self.font_scale_large = 1.0
        self.thickness_thin = 1
        self.thickness_med = 2
        
        self.colors = {
            'text': (255, 255, 255),
            'header': (0, 255, 255),
            'bg': (0, 0, 0),
            'optimal': (0, 255, 0),
            'warning': (0, 165, 255),
            'danger': (0, 0, 255)
        }

    def render(self, frame, stats, session_stats, fatigue_status):
        if not self.enabled:
            return frame

        h, w, _ = frame.shape
        
        # --- LEFT PANEL (Biomechanics) ---
        overlay_left = frame.copy()
        cv2.rectangle(overlay_left, (10, 10), (260, 280), self.colors['bg'], -1)
        frame = cv2.addWeighted(overlay_left, 0.6, frame, 0.4, 0)
        
        y = 40
        x = 20
        cv2.putText(frame, f"MODE: {stats.get('mode', 'N/A')}", (x, y), self.font, self.font_scale_med, self.colors['header'], 2)
        y += 35
        cv2.putText(frame, f"STATE: {stats.get('state', 'N/A')}", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)
        y += 35
        cv2.putText(frame, f"ANGLE: {int(stats.get('angle', 0))} deg", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)
        y += 35
        cv2.putText(frame, f"ELBOW: {int(stats.get('elbow_angle', 0))} deg", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)
        y += 35
        cv2.putText(frame, f"STABILITY: {stats.get('stability', 0.0):.3f}", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)
        y += 35
        vis = stats.get('visibility', 0.0)
        vis_color = self.colors['optimal'] if vis > 0.6 else self.colors['danger']
        cv2.putText(frame, f"VISIBILITY: {vis:.2f}", (x, y), self.font, self.font_scale_med, vis_color, 2)

        # --- RIGHT PANEL (Score & Reps) ---
        overlay_right = frame.copy()
        cv2.rectangle(overlay_right, (w-260, 10), (w-10, 240), self.colors['bg'], -1)
        frame = cv2.addWeighted(overlay_right, 0.6, frame, 0.4, 0)
        
        y = 40
        x = w - 240
        cv2.putText(frame, f"REP: {stats.get('rep_count', 0)}", (x, y), self.font, self.font_scale_large, self.colors['header'], 3)
        y += 45
        score = stats.get('score', 100)
        score_color = self.colors['optimal'] if score > 80 else self.colors['warning'] if score > 50 else self.colors['danger']
        cv2.putText(frame, f"SCORE: {int(score)}", (x, y), self.font, self.font_scale_large, score_color, 3)
        y += 40
        cv2.putText(frame, f"ERRORS: {stats.get('error_count', 0)}", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)
        y += 35
        cv2.putText(frame, f"HOLD TIME: {stats.get('hold_time', 0.0):.2f}s", (x, y), self.font, self.font_scale_med, self.colors['text'], 2)

        # --- BOTTOM BAR (Session) ---
        overlay_bottom = frame.copy()
        cv2.rectangle(overlay_bottom, (10, h-80), (w-10, h-10), self.colors['bg'], -1)
        frame = cv2.addWeighted(overlay_bottom, 0.6, frame, 0.4, 0)
        
        x_offsets = [20, w//3 + 20, 2*w//3 + 20]
        y = h - 35
        cv2.putText(frame, f"SESSION AVG: {int(session_stats.get('avg_score', 0))}", (x_offsets[0], y), self.font, self.font_scale_med, self.colors['text'], 2)
        cv2.putText(frame, f"BEST REP: {int(session_stats.get('best_rep', 0))}", (x_offsets[1], y), self.font, self.font_scale_med, self.colors['text'], 2)
        f_color = self.colors['optimal'] if fatigue_status == "OPTIMAL" else self.colors['danger']
        cv2.putText(frame, f"FATIGUE: {fatigue_status}", (x_offsets[2], y), self.font, self.font_scale_med, f_color, 2)

        # --- FEEDBACK POPUP (Dynamic) ---
        errors = stats.get('errors', [])
        if errors:
            msg = errors[0]['msg']
            msg_w = cv2.getTextSize(msg, self.font, 1.2, 3)[0][0]
            cv2.rectangle(frame, (w//2 - msg_w//2 - 20, 300), (w//2 + msg_w//2 + 20, 370), (0, 0, 150), -1)
            cv2.putText(frame, msg, (w//2 - msg_w//2, 350), self.font, 1.2, (255, 255, 255), 3)

        return frame
