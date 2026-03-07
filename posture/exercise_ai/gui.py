import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from main import ExerciseEngine
import threading
import time

class ExerciseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Exercise Coach - Posture Pro")
        # Start maximized for "Full Screen" feel
        self.after(0, lambda: self.state('zoomed'))
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = None
        self.is_running = False
        self.current_exercise = None

        # Main Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="POSTURE PRO", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=30)

        # Exercise Buttons with Icons
        self.load_icons()
        
        self.squat_btn = self.create_nav_button("Squats", "squat", self.squat_icon)
        self.pushup_btn = self.create_nav_button("Push-ups", "pushup", self.pushup_icon)
        self.stretch_btn = self.create_nav_button("Side Weight Holding", "sidearm", self.stretch_icon)

        self.stop_btn = ctk.CTkButton(self.sidebar, text="STOP WORKOUT", fg_color="#d32f2f", hover_color="#b71c1c",
                                     command=self.stop_workout, state="disabled")
        self.stop_btn.pack(side="bottom", pady=40, padx=20)

        # Content Area - Fully expand camera
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Camera Display - Full area
        self.camera_label = ctk.CTkLabel(self.content, text="", fg_color="#1a1a1a", corner_radius=20)
        self.camera_label.grid(row=0, column=0, sticky="nsew")

        # Stats Dashboard - Right side
        self.stats_frame = ctk.CTkFrame(self.content, width=300, corner_radius=20)
        self.stats_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        
        self.setup_stats_ui()

        # Initial Welcome
        self.welcome_screen()

    def load_icons(self):
        try:
            self.squat_icon = ctk.CTkImage(Image.open("squat_icon.png"), size=(40, 40))
            self.pushup_icon = ctk.CTkImage(Image.open("pushup_icon.png"), size=(40, 40))
            self.stretch_icon = ctk.CTkImage(Image.open("stretch_icon.png"), size=(40, 40))
        except:
            self.squat_icon = self.pushup_icon = self.stretch_icon = None

    def create_nav_button(self, name, ex_type, icon):
        btn = ctk.CTkButton(self.sidebar, text=name, image=icon, compound="left", 
                            height=60, font=ctk.CTkFont(size=14, weight="bold"),
                            anchor="w", command=lambda: self.start_workout(ex_type))
        btn.pack(pady=10, padx=20, fill="x")
        return btn

    def setup_stats_ui(self):
        ctk.CTkLabel(self.stats_frame, text="LIVE SESSION", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00ffff").pack(pady=(20, 10))
        
        # Session Timer
        self.timer_label = ctk.CTkLabel(self.stats_frame, text="00:00", font=ctk.CTkFont(size=32, weight="bold"), text_color="#ffffff")
        self.timer_label.pack(pady=5)
        ctk.CTkLabel(self.stats_frame, text="ELAPSED TIME", font=ctk.CTkFont(size=12)).pack()

        # Divider
        ctk.CTkFrame(self.stats_frame, height=2, fg_color="#444444").pack(fill="x", padx=20, pady=20)

        self.rep_title = ctk.CTkLabel(self.stats_frame, text="REPS / HOLD", font=ctk.CTkFont(size=14))
        self.rep_title.pack()
        self.rep_val = ctk.CTkLabel(self.stats_frame, text="0", font=ctk.CTkFont(size=56, weight="bold"), text_color="#ffcc00")
        self.rep_val.pack(pady=5)

        # Form Scores
        self.score_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.score_frame.pack(fill="x", padx=10)
        
        # Current Score
        cur_sc_cnt = ctk.CTkFrame(self.score_frame, fg_color="#2b2b2b", corner_radius=10)
        cur_sc_cnt.pack(side="left", expand=True, fill="both", padx=5, pady=10)
        ctk.CTkLabel(cur_sc_cnt, text="CURRENT", font=ctk.CTkFont(size=10)).pack(pady=(5,0))
        self.score_val = ctk.CTkLabel(cur_sc_cnt, text="100%", font=ctk.CTkFont(size=20, weight="bold"))
        self.score_val.pack(pady=(0,5))

        # Avg Score
        avg_sc_cnt = ctk.CTkFrame(self.score_frame, fg_color="#2b2b2b", corner_radius=10)
        avg_sc_cnt.pack(side="left", expand=True, fill="both", padx=5, pady=10)
        ctk.CTkLabel(avg_sc_cnt, text="AVG PERFORMANCE", font=ctk.CTkFont(size=10)).pack(pady=(5,0))
        self.avg_score_val = ctk.CTkLabel(avg_sc_cnt, text="100%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00ffcc")
        self.avg_score_val.pack(pady=(0,5))

        self.score_bar = ctk.CTkProgressBar(self.stats_frame, width=220, height=12)
        self.score_bar.pack(pady=10)

        self.feedback_frame = ctk.CTkFrame(self.stats_frame, fg_color="#1e1e1e", border_width=1, border_color="#00ffff", corner_radius=15)
        self.feedback_frame.pack(fill="x", padx=20, pady=20)
        self.feedback_label = ctk.CTkLabel(self.feedback_frame, text="Ready to track\nyour progress", 
                                          font=ctk.CTkFont(size=16, slant="italic"), wraplength=200, text_color="#00ffff")
        self.feedback_label.pack(pady=20)

    def welcome_screen(self):
        self.camera_label.configure(image="", text="POSTURE PRO AI\n\nSelect an exercise to begin your professional training session.",
                                   font=ctk.CTkFont(size=28, weight="bold"), text_color="#555555")

    def start_workout(self, ex_type):
        if self.is_running: self.stop_workout()
        
        self.current_exercise = ex_type
        self.is_running = True
        self.engine = ExerciseEngine(ex_type)
        
        self.stop_btn.configure(state="normal")
        self.camera_label.configure(text="")
        
        # Start update loop
        self.update_frame()

    def stop_workout(self):
        self.is_running = False
        if self.engine:
            self.engine.release()
            self.engine = None
        self.stop_btn.configure(state="disabled")
        self.welcome_screen()

    def update_frame(self):
        if not self.is_running or not self.engine: return

        frame, stats = self.engine.get_frame()
        if frame is not None:
            # Time Formatting
            mins, secs = divmod(stats['elapsed_time'], 60)
            self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")

            # Stats Update
            self.rep_val.configure(text=str(stats['counter']))
            self.score_val.configure(text=f"{int(stats['form_score'])}%")
            self.avg_score_val.configure(text=f"{int(stats['avg_score'])}%")
            self.score_bar.set(stats['form_score'] / 100.0)
            self.feedback_label.configure(text=stats['feedback'])
            
            # Color update for score
            if stats['form_score'] > 80: 
                self.score_val.configure(text_color="#00ff00")
                self.score_bar.configure(progress_color="#00ff00")
            elif stats['form_score'] > 50: 
                self.score_val.configure(text_color="#ffa500")
                self.score_bar.configure(progress_color="#ffa500")
            else: 
                self.score_val.configure(text_color="#ff0000")
                self.score_bar.configure(progress_color="#ff0000")

            # Convert frame to CTkImage
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            
            # Scale to fit label - Optimization: Using BILINEAR
            w, h = self.camera_label.winfo_width(), self.camera_label.winfo_height()
            if w > 10 and h > 10:
                img = img.resize((w, h), Image.Resampling.BILINEAR)
            
            ctk_img = ImageTk.PhotoImage(img) # Stable rendering
            self.camera_label.configure(image=ctk_img)
            self.camera_label._image = ctk_img # Keep reference

        self.after(30, self.update_frame)

if __name__ == "__main__":
    app = ExerciseApp()
    app.mainloop()
