import time

class LateralRaiseState:
    REST = "REST"
    LIFTING = "LIFTING"
    HOLD = "HOLD"
    LOWERING = "LOWERING"

class LateralRaiseStateMachine:
    def __init__(self):
        self.state = LateralRaiseState.REST
        self.hold_frames = 0
        self.hold_start_time = None
        self.rep_counted = False
        self.reps = 0
        self.hold_duration = 0.0

    def update(self, angle, stability_variance):
        prev_state = self.state
        
        # 3️⃣ CORRECT STATE MACHINE LOGIC
        # REST -> LIFTING Triggered only when angle > 30°
        if self.state == LateralRaiseState.REST:
            if angle > 30:
                self.state = LateralRaiseState.LIFTING
                self.rep_counted = False
        
        # LIFTING -> HOLD Triggered when angle within 85–95° for 3+ frames
        elif self.state == LateralRaiseState.LIFTING:
            if 85 <= angle <= 95:
                self.hold_frames += 1
                if self.hold_frames >= 3:
                    self.state = LateralRaiseState.HOLD
                    self.hold_start_time = time.time()
            elif angle < 25: # Aborted rep
                self.state = LateralRaiseState.REST
            else:
                self.hold_frames = 0 # Must be consecutive
                
        # HOLD -> LOWERING Triggered when angle drops below 80°
        elif self.state == LateralRaiseState.HOLD:
            if angle < 80:
                self.state = LateralRaiseState.LOWERING
                if self.hold_start_time:
                    self.hold_duration = time.time() - self.hold_start_time
            elif angle > 115: # Over-lifting
                self.state = LateralRaiseState.LOWERING
            
        # LOWERING -> REST Triggered when angle < 25°
        elif self.state == LateralRaiseState.LOWERING:
            if angle < 25:
                self.state = LateralRaiseState.REST
                if not self.rep_counted:
                    self.reps += 1
                    self.rep_counted = True
                    self.hold_frames = 0
        
        return self.state, self.state != prev_state

    def cancel_last_rep(self):
        if self.rep_counted and self.reps > 0:
            self.reps -= 1
            self.rep_counted = False
class PushupState:
    REST = "REST"
    DESCENDING = "DESCENDING"
    BOTTOM = "BOTTOM"
    ASCENDING = "ASCENDING"

class PushupStateMachine:
    def __init__(self):
        self.state = PushupState.REST
        self.reps = 0
        self.rep_counted = False
        self.hold_start_time = None
        self.hold_duration = 0
        self.lowest_angle = 180.0
        self.consecutive_frames = 0

    def update(self, angle, stability_variance):
        prev_state = self.state
        
        # Hysteresis: Require matching frames for transition
        target_state = self.state
        
        if self.state == PushupState.REST:
            if angle < 160: 
                target_state = PushupState.DESCENDING
        
        elif self.state == PushupState.DESCENDING:
            if angle < 100: 
                target_state = PushupState.BOTTOM
            elif angle > 165: 
                target_state = PushupState.REST
            
        elif self.state == PushupState.BOTTOM:
            if angle > 115: 
                target_state = PushupState.ASCENDING
            elif angle > 135: 
                target_state = PushupState.REST
        
        elif self.state == PushupState.ASCENDING:
            if angle > 165: 
                target_state = PushupState.REST
            elif angle < 105: 
                target_state = PushupState.DESCENDING

        if target_state != self.state:
            self.consecutive_frames += 1
            if self.consecutive_frames >= 3:
                self.state = target_state
                self.consecutive_frames = 0
                if self.state == PushupState.DESCENDING:
                    self.rep_counted = False
                    self.lowest_angle = 180
                elif self.state == PushupState.BOTTOM:
                    self.hold_start_time = time.time()
                elif self.state == PushupState.ASCENDING:
                    if self.hold_start_time:
                        self.hold_duration = time.time() - self.hold_start_time
                elif self.state == PushupState.REST:
                    if not self.rep_counted and prev_state == PushupState.ASCENDING:
                        self.reps += 1
                        self.rep_counted = True
        else:
            self.consecutive_frames = 0

        self.lowest_angle = min(self.lowest_angle, angle)
        return self.state, self.state != prev_state

    def cancel_last_rep(self):
        if self.reps > 0:
            self.reps -= 1
            self.rep_counted = False
