import time

class SessionLogger:
    def __init__(self):
        self.session_log = []
        self.start_time = time.time()

    def log_rep(self, rep_data):
        """
        rep_data expecting:
        {
            'max_angle': float,
            'hold_duration': float,
            'lift_time': float,
            'lower_time': float,
            'avg_stability': float,
            'visibility_score': float,
            'error_count': int,
            'final_score': float
        }
        """
        log_entry = {
            'rep_number': len(self.session_log) + 1,
            'timestamp': time.time()
        }
        log_entry.update(rep_data)
        self.session_log.append(log_entry)

    def get_avg_score(self):
        if not self.session_log: return 100
        return sum(r['final_score'] for r in self.session_log) / len(self.session_log)

    def get_best_rep_score(self):
        if not self.session_log: return 0
        return max(r['final_score'] for r in self.session_log)

    def get_session_stats(self):
        return {
            'avg_score': self.get_avg_score(),
            'best_rep': self.get_best_rep_score(),
            'total_reps': len(self.session_log)
        }
