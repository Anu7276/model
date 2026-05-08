import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXERCISE_AI_PATH = os.path.join(BASE_DIR, "posture", "exercise_ai")
sys.path.append(EXERCISE_AI_PATH)

print(f"Checking imports in {EXERCISE_AI_PATH}...")

try:
    from squat_v2 import SquatV2Coach
    print("Success: squat_v2")
except Exception as e:
    print(f"Error: squat_v2 - {e}")

try:
    from pushup_v2 import PushupV2Coach
    print("Success: pushup_v2")
except Exception as e:
    print(f"Error: pushup_v2 - {e}")

try:
    from side_arm_v2 import SideArmV2Coach
    print("Success: side_arm_v2")
except Exception as e:
    print(f"Error: side_arm_v2 - {e}")
