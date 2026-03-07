import numpy as np

def calculate_angle(a, b, c):
    """
    Calculates the angle at point b given three points a, b, c.
    Each point is an [x, y] coordinate.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - \
              np.arctan2(a[1]-b[1], a[0]-b[0])
    # Use vectors to be more robust and readable
    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return np.degrees(angle)

def calculate_horizontal_elevation(shoulder, elbow):
    """
    Calculates the angle of the upper arm relative to the horizontal plane.
    0° = arm down, 90° = arm parallel to ground.
    """
    # Vector from shoulder to elbow
    dx = elbow[0] - shoulder[0]
    dy = shoulder[1] - elbow[1] # standard y-down flip
    
    # atan2(y, x) gives radians from horizontal
    angle_rad = np.arctan2(dy, abs(dx))
    return np.degrees(angle_rad)

def calculate_torso_tilt(mid_shoulder, mid_hip):
    """
    Calculates how much the torso is tilting away from vertical (y-axis).
    """
    dx = mid_shoulder[0] - mid_hip[0]
    dy = mid_hip[1] - mid_shoulder[1]
    
    angle_rad = np.arctan2(abs(dx), dy)
    return np.degrees(angle_rad)

class JitterFilter:
    """One-pole EMA filter for signal smoothing."""
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.prev_value = None

    def filter(self, current_value):
        if self.prev_value is None:
            self.prev_value = current_value
            return current_value
        
        smoothed = (1 - self.alpha) * self.prev_value + self.alpha * current_value
        self.prev_value = smoothed
        return smoothed

class DynamicBaselineTracker:
    """Learns personalized biomechanical ranges over time."""
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.current_baseline = None
        
    def update(self, value):
        if self.current_baseline is None:
            self.current_baseline = value
        else:
            self.current_baseline = (1 - self.alpha) * self.current_baseline + self.alpha * value
        return self.current_baseline

    def get(self):
        return self.current_baseline
