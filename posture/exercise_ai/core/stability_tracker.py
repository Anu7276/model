import numpy as np
from collections import deque

class StabilityTracker:
    def __init__(self, size=15):
        self.buffer = deque(maxlen=size)
        self.smoothness_index = 0.0

    def update(self, value):
        self.buffer.append(value)
        if len(self.buffer) < 5: # Need enough for variance
            return 0.0
            
        # 8️⃣ IMPROVE STABILITY METRIC - Use rolling variance of last 15 frames
        variance = np.var(self.buffer)
        
        # Calculate Smoothness Index
        diffs = np.diff(list(self.buffer))
        self.smoothness_index = np.sum(np.abs(diffs))
            
        return variance

    def get_smoothness(self):
        return self.smoothness_index
