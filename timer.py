#!/usr/bin/env python3
"""
Razor Pomodoro Timer
Floating widget. Collapsible. Skip, sound picker, model selector.
"""

import json
import platform
import subprocess
import threading
import time
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    from playsound import playsound as _playsound
    HAS_PLAYSOUND = True
except ImportError:
    HAS_PLAYSOUND = False

import sys
_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG_PATH = _BASE / "config.json"

DEFAULT_CONFIG = {
    "mode": "25/5",
    "modes": {
        "25/5":  {"work": 25, "break": 5},
        "50/10": {"work": 50, "break": 10},
    },
    "always_on_top": True,
    "sound": "beep",          # "beep" | "silent" | "/path/to/file.wav"
    "window_x": 100,
    "window_y": 100,
}

C = {
    "work":   "#E05C5C",
    "break":  "#5CA65C",
    "bg":     "#1a1a2e",
    "bar":    "#16213e",
    "accent": "#0f3460",
    "text":   "#e0e0e0",
    "muted":  "#666666",
    "dim":    "#2a2a4a",
}

SOUND_OPTIONS = ["beep", "silent", "custom..."]


# ── Sound ─────────────────────────────────────────────────────────────────────

def play_sound(sound: str):
    """Play beep, silent, or a custom file path."""
    if sound == "silent" or sound == "custom...":
        return
    if sound == "beep":
        try:
            if platform.system() == "Windows":
                import winsound
                for freq, dur in [(880, 180), (1100, 180), (1320, 280)]:
                    winsound.Beep(freq, dur)
            elif platform.system() == "Darwin":
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            else:
                subprocess.run(
                    ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                    check=False,
                )
        except Exception:
            pass
        return
    # Custom file path
    path = Path(sound)
    if not path.exists():
        return
    try:
        if HAS_PLAYSOUND:
            threading.Thread(target=_playsound, args=(str(path),), daemon=True).start()
        elif platform.system() == "Darwin":
            subprocess.run(["afplay", str(path)], check=False)
        else:
            subprocess.run(["paplay", str(path)], check=False)
    except Exception:
        pass


# ── App ───────────────────────────────────────────────────────────────────────

class RazorTimer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = self._load_config()
        self.collapsed = False
        self._expanded_h = 0
        self.running = False
        self.phase = "work"
        self.session_count = 0
        self.time_remaining = 0
        self._setup_window()
        self._build_ui()
        self.reset_timer()
        # Cache expanded height after first render
        self.after(100, self._cache_height)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.cfg, f, indent=2)

    def _cache_height(self):
        self.update_idletasks()
        self._expanded_h = self.winfo_height()

    # ── Window ────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Razor")
        self.overrideredirect(True)
        self.attributes("-topmost", self.cfg["always_on_top"])
        self.configure(fg_color=C["bg"])
        self.geometry(f"300x420+{self.cfg['window_x']}+{self.cfg['window_y']}")
        self._dx = self._dy = 0

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_titlebar()
        self._build_body()

    def _build_titlebar(self):
        self.bar = ctk.CTkFrame(self, fg_color=C["bar"], corner_radius=6, height=34)
        self.bar.pack(fill="x")
        self.bar.pack_propagate(False)

        for w in (self.bar,):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_stop)

        lbl = ctk.CTkLabel(self.bar, text="● RAZOR",
                           font=("Courier New", 11, "bold"), text_color=C["text"])
        lbl.pack(side="left", padx=8)
        lbl.bind("<ButtonPress-1>", self._drag_start)
        lbl.bind("<B1-Motion>", self._drag_move)

        self.lbl_bar_info = ctk.CTkLabel(self.bar, text="",
                                         font=("Courier New", 11), text_color=C["work"])
        self.lbl_bar_info.pack(side="left", padx=2)
        self.lbl_bar_info.bind("<ButtonPress-1>", self._drag_start)
        self.lbl_bar_info.bind("<B1-Motion>", self._drag_move)

        # Close
        ctk.CTkButton(self.bar, text="×", width=26, height=24,
                      font=("Arial", 14), fg_color="transparent",
                      hover_color="#8b0000", text_color=C["text"],
                      command=self._quit).pack(side="right", padx=2, pady=4)

        # Expand/collapse — always in title bar
        self.btn_toggle = ctk.CTkButton(
            self.bar, text="▲", width=26, height=24,
            font=("Arial", 9), fg_color="transparent",
            hover_color=C["accent"], text_color=C["text"],
            command=self.toggle_collapse
        )
        self.btn_toggle.pack(side="right", padx=2, pady=4)

    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Phase
        self.lbl_phase = ctk.CTkLabel(self.body, text="WORK SESSION",
                                      font=("Courier New", 12, "bold"),
                                      text_color=C["work"])
        self.lbl_phase.pack(pady=(12, 0))

        # Countdown
        self.lbl_time = ctk.CTkLabel(self.body, text="25:00",
                                     font=("Courier New", 52, "bold"),
                                     text_color=C["text"])
        self.lbl_time.pack(pady=(2, 8))

        # Controls row: START | RESET | SKIP
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(pady=4)

        self.btn_start = ctk.CTkButton(
            row, text="START", width=88,
            font=("Courier New", 12, "bold"),
            fg_color=C["work"], hover_color="#a03030",
            command=self.toggle_timer
        )
        self.btn_start.pack(side="left", padx=3)

        ctk.CTkButton(row, text="RESET", width=68,
                      font=("Courier New", 11),
                      fg_color=C["accent"], hover_color="#1a4a8a",
                      command=self.reset_timer).pack(side="left", padx=3)

        ctk.CTkButton(row, text="⏭", width=40,
                      font=("Arial", 14),
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"],
                      command=self.skip_phase).pack(side="left", padx=3)

        # Session counter
        self.lbl_session = ctk.CTkLabel(self.body, text="Session 0",
                                        font=("Courier New", 10),
                                        text_color=C["muted"])
        self.lbl_session.pack(pady=(8, 2))

        # Mode selector
        mrow = ctk.CTkFrame(self.body, fg_color="transparent")
        mrow.pack(pady=4)
        self.mode_var = ctk.StringVar(value=self.cfg["mode"])
        for mode in self.cfg["modes"]:
            ctk.CTkRadioButton(mrow, text=mode, variable=self.mode_var, value=mode,
                               font=("Courier New", 10), text_color=C["text"],
                               command=self.change_mode).pack(side="left", padx=10)

        # Divider
        ctk.CTkFrame(self.body, fg_color=C["dim"], height=1).pack(fill="x", pady=6)

        # Settings row
        self._build_settings()

    def _build_settings(self):
        srow = ctk.CTkFrame(self.body, fg_color="transparent")
        srow.pack(fill="x", pady=(0, 2))

        # Sound label
        ctk.CTkLabel(srow, text="Sound:", font=("Courier New", 10),
                     text_color=C["muted"]).pack(side="left", padx=(4, 2))

        # Resolve display value for dropdown
        saved = self.cfg.get("sound", "beep")
        display = saved if saved in ("beep", "silent") else "custom..."
        self.sound_var = ctk.StringVar(value=display)

        ctk.CTkOptionMenu(srow, values=SOUND_OPTIONS, variable=self.sound_var,
                          width=100, height=24,
                          font=("Courier New", 10),
                          fg_color=C["accent"], button_color=C["dim"],
                          command=self._sound_changed).pack(side="left", padx=4)

        # Always on top
        self.aot_var = ctk.BooleanVar(value=self.cfg["always_on_top"])
        ctk.CTkCheckBox(srow, text="Top", variable=self.aot_var,
                        font=("Courier New", 10), text_color=C["muted"],
                        width=50, command=self._toggle_aot).pack(side="right", padx=4)

        # Custom file label (shows filename when custom is set)
        self.lbl_sound_file = ctk.CTkLabel(
            self.body, text=self._custom_sound_label(),
            font=("Courier New", 9), text_color=C["muted"]
        )
        self.lbl_sound_file.pack(pady=(0, 4))

    # ── Collapse ──────────────────────────────────────────────────────────────

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self._expanded_h = self.winfo_height()
            self.body.pack_forget()
            self.update_idletasks()
            self.geometry(f"300x34+{self.winfo_x()}+{self.winfo_y()}")
            self.btn_toggle.configure(text="▼")
            self._refresh_bar_info()
        else:
            self.body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.update_idletasks()
            h = self._expanded_h if self._expanded_h > 34 else self.winfo_reqheight()
            self.geometry(f"300x{h}+{self.winfo_x()}+{self.winfo_y()}")
            self.btn_toggle.configure(text="▲")
            self.lbl_bar_info.configure(text="")

    def _refresh_bar_info(self):
        if not self.collapsed:
            return
        label = "WORK" if self.phase == "work" else "BREAK"
        color = C["work"] if self.phase == "work" else C["break"]
        m, s = divmod(self.time_remaining, 60)
        self.lbl_bar_info.configure(text=f"| {label}  {m:02d}:{s:02d}", text_color=color)

    # ── Timer ─────────────────────────────────────────────────────────────────

    def reset_timer(self):
        self.running = False
        self.phase = "work"
        work = self.cfg["modes"][self.cfg["mode"]]["work"]
        self.time_remaining = work * 60
        self.btn_start.configure(text="START", fg_color=C["work"], hover_color="#a03030")
        self.lbl_phase.configure(text="WORK SESSION", text_color=C["work"])
        self.lbl_time.configure(text=self._fmt(self.time_remaining), text_color=C["text"])
        self._refresh_bar_info()

    def toggle_timer(self):
        if self.running:
            self.running = False
            self.btn_start.configure(text="RESUME")
        else:
            self.running = True
            self.btn_start.configure(text="PAUSE")
            threading.Thread(target=self._tick, daemon=True).start()

    def skip_phase(self):
        self.running = False
        self.time_remaining = 0
        self.after(50, self._phase_done)

    def _tick(self):
        while self.running and self.time_remaining > 0:
            time.sleep(1)
            if self.running:
                self.time_remaining -= 1
                self.after(0, self._update_display)
        if self.time_remaining <= 0 and self.running:
            self.after(0, self._phase_done)

    def _update_display(self):
        self.lbl_time.configure(text=self._fmt(self.time_remaining))
        self._refresh_bar_info()

    def _phase_done(self):
        self.running = False
        play_sound(self.cfg.get("sound", "beep"))
        self._desktop_notify()

        if self.phase == "work":
            self.session_count += 1
            self.lbl_session.configure(text=f"Session {self.session_count}")
            self.phase = "break"
            secs = self.cfg["modes"][self.cfg["mode"]]["break"] * 60
            self.lbl_phase.configure(text="BREAK", text_color=C["break"])
            self.lbl_time.configure(text_color=C["break"])
            self.btn_start.configure(text="START BREAK",
                                     fg_color=C["break"], hover_color="#307830")
        else:
            self.phase = "work"
            secs = self.cfg["modes"][self.cfg["mode"]]["work"] * 60
            self.lbl_phase.configure(text="WORK SESSION", text_color=C["work"])
            self.lbl_time.configure(text_color=C["text"])
            self.btn_start.configure(text="START",
                                     fg_color=C["work"], hover_color="#a03030")

        self.time_remaining = secs
        self._update_display()

    def _desktop_notify(self):
        if self.phase == "work":
            title, msg = "Razor — Break Time", "Session done. Take a break."
        else:
            title, msg = "Razor — Work Time", "Break over. Back to it."
        if HAS_PLYER:
            try:
                notification.notify(title=title, message=msg,
                                    app_name="Razor", timeout=5)
            except Exception:
                pass

    # ── Settings callbacks ────────────────────────────────────────────────────

    def change_mode(self):
        self.cfg["mode"] = self.mode_var.get()
        self._save_config()
        self.reset_timer()

    def _sound_changed(self, value):
        if value == "custom...":
            path = filedialog.askopenfilename(
                title="Choose alert sound",
                filetypes=[("Audio files", "*.wav *.mp3 *.aiff *.ogg"), ("All files", "*.*")]
            )
            if path:
                self.cfg["sound"] = path
                self._save_config()
                play_sound(path)
            else:
                # Revert dropdown if cancelled
                saved = self.cfg.get("sound", "beep")
                self.sound_var.set(saved if saved in ("beep", "silent") else "custom...")
        else:
            self.cfg["sound"] = value
            self._save_config()
            play_sound(value)
        self.lbl_sound_file.configure(text=self._custom_sound_label())

    def _custom_sound_label(self):
        saved = self.cfg.get("sound", "beep")
        if saved not in ("beep", "silent"):
            return f"  {Path(saved).name}"
        return ""

    def _toggle_aot(self):
        self.cfg["always_on_top"] = self.aot_var.get()
        self.attributes("-topmost", self.cfg["always_on_top"])
        self._save_config()

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.winfo_x() + e.x - self._dx
        y = self.winfo_y() + e.y - self._dy
        self.geometry(f"+{x}+{y}")

    def _drag_stop(self, e):
        self.cfg["window_x"] = self.winfo_x()
        self.cfg["window_y"] = self.winfo_y()
        self._save_config()

    # ── Util ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _quit(self):
        self.running = False
        self._save_config()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    RazorTimer().mainloop()
