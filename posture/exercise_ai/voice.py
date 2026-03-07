"""
voice.py — Advanced Voice System
- Non-blocking TTS with priority queue
- Voice command recognition (speech-to-text)
- Smart cooldown with per-category deduplication
- Emotion-aware speech rate/volume
"""

import time
import threading
from queue import PriorityQueue, Empty
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# ── TTS Engine ────────────────────────────────────────────────────────────────

_tts_queue: PriorityQueue = PriorityQueue()
_last_spoken: dict = {}          # category → timestamp
_cooldowns: dict = {             # per-category cooldown (seconds)
    "rep":       1.5,
    "form":      3.0,
    "warning":   2.5,
    "milestone": 0.0,
    "system":    0.0,
    "default":   2.5,
}
_lock = threading.Lock()
_enabled = True
_tts_available = pyttsx3 is not None


def _tts_worker():
    global _tts_available
    if not _tts_available:
        return

    try:
        engine = pyttsx3.init()
    except Exception:
        _tts_available = False
        return

    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    # Prefer a clear female voice if available
    for v in voices:
        if "zira" in v.name.lower() or "female" in v.name.lower():
            engine.setProperty("voice", v.id)
            break

    while True:
        try:
            priority, text, rate = _tts_queue.get(timeout=0.5)
            if not _enabled:
                _tts_queue.task_done()
                continue
            engine.setProperty("rate", rate)
            engine.say(text)
            engine.runAndWait()
            _tts_queue.task_done()
        except Empty:
            pass
        except Exception as e:
            print(f"[Voice TTS Error] {e}")


threading.Thread(target=_tts_worker, daemon=True).start()


def speak(text: str, category: str = "default", priority: int = 5, rate: int = 165):
    """
    Speak text if cooldown for this category has passed.
    Lower priority number = spoken sooner.
    """
    if not text or not _enabled or not _tts_available:
        return
    now = time.time()
    cooldown = _cooldowns.get(category, _cooldowns["default"])
    with _lock:
        last = _last_spoken.get(category, 0)
        if now - last < cooldown:
            return
        _last_spoken[category] = now
    _tts_queue.put((priority, text, rate))


def speak_rep(count: int, score: int = None):
    if score is not None and score >= 90:
        msg = f"Rep {count}. Perfect!"
        rate = 175
    elif score is not None and score < 60:
        msg = f"Rep {count}. Work on your form."
        rate = 155
    else:
        msg = f"Rep {count}"
        rate = 165
    speak(msg, category="rep", priority=2, rate=rate)


def speak_milestone(reps: int):
    milestones = {5: "Five reps, keep going!", 10: "Ten reps! Great work!", 
                  15: "Fifteen! You're on fire!", 20: "Twenty reps! Beast mode!",
                  25: "Twenty five! Incredible!", 30: "Thirty reps! Legendary!"}
    if reps in milestones:
        speak(milestones[reps], category="milestone", priority=1, rate=175)


def speak_warning(msg: str):
    speak(msg, category="warning", priority=3, rate=155)


def speak_form(msg: str):
    speak(msg, category="form", priority=4, rate=160)


def speak_system(msg: str):
    speak(msg, category="system", priority=1, rate=165)


def set_enabled(val: bool):
    global _enabled
    _enabled = val


# ── Voice Command Recognition ─────────────────────────────────────────────────

_command_callback = None
_listening = False
_recognizer = None
_mic = None


def _init_recognizer():
    global _recognizer, _mic
    try:
        import speech_recognition as sr
        _recognizer = sr.Recognizer()
        _recognizer.energy_threshold = 300
        _recognizer.dynamic_energy_threshold = True
        _recognizer.pause_threshold = 0.6
        _mic = sr.Microphone()
        return True
    except ImportError:
        print("[Voice] speech_recognition not installed. Voice commands disabled.")
        return False
    except Exception as e:
        print(f"[Voice] Mic init failed: {e}")
        return False


COMMANDS = {
    # Start/Stop
    "start":         ("start", "begin", "go", "start workout", "begin workout"),
    "stop":          ("stop", "end", "quit", "stop workout", "finish"),
    "pause":         ("pause", "hold on", "wait"),
    "resume":        ("resume", "continue", "keep going"),
    # Exercise selection
    "pushup":        ("push up", "pushup", "push-up", "chest"),
    "squat":         ("squat", "squats", "legs"),
    "sidearm":       ("side arm", "side raise", "side weight hold", "side weight holding", "lateral raise", "shoulder", "stretch"),
    # Settings
    "mute":          ("mute", "quiet", "silence", "shut up"),
    "unmute":        ("unmute", "sound on", "voice on"),
    # Feedback
    "score":         ("score", "my score", "how am i doing", "form score"),
    "reps":          ("reps", "count", "how many", "rep count"),
    "reset":         ("reset", "start over", "restart"),
}


def _listen_loop():
    global _listening
    import speech_recognition as sr

    with _mic as source:
        _recognizer.adjust_for_ambient_noise(source, duration=1)
    
    print("[Voice] Command listener active.")
    while _listening:
        try:
            with _mic as source:
                audio = _recognizer.listen(source, timeout=3, phrase_time_limit=4)
            text = _recognizer.recognize_google(audio).lower().strip()
            print(f"[Voice CMD] Heard: '{text}'")
            _dispatch_command(text)
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"[Voice CMD Error] {e}")
            time.sleep(0.5)


def _dispatch_command(text: str):
    for cmd_key, phrases in COMMANDS.items():
        for phrase in phrases:
            if phrase in text:
                if _command_callback:
                    _command_callback(cmd_key)
                return


def start_listening(callback):
    """Start background voice command recognition. callback(command_key) is called on match."""
    global _listening, _command_callback
    if not _init_recognizer():
        return False
    _command_callback = callback
    _listening = True
    t = threading.Thread(target=_listen_loop, daemon=True)
    t.start()
    return True


def stop_listening():
    global _listening
    _listening = False
