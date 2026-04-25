#!/usr/bin/env python3
"""
Razor Pomodoro Timer
Floating widget. Collapsible. Declare, work, report loop.
"""

import datetime
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

import os
import sys

def _config_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".config"
    d = base / "razor"
    d.mkdir(parents=True, exist_ok=True)
    return d

CONFIG_PATH = _config_dir() / "config.json"
LOG_DIR     = Path.home() / "Documents" / "razor"

DEFAULT_CONFIG = {
    "mode": "25/5",
    "modes": {
        "25/5":  {"work": 25, "break": 5},
        "50/10": {"work": 50, "break": 10},
    },
    "always_on_top": True,
    "sound": "beep",
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
    "done":   "#5CA65C",
}

SOUND_OPTIONS = ["beep", "silent", "custom..."]


# ── Sound ─────────────────────────────────────────────────────────────────────

def play_sound(sound: str):
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


# ── Declaration dialog ────────────────────────────────────────────────────────

class _DeclarationDialog(ctk.CTkToplevel):
    def __init__(self, parent, prefill=""):
        super().__init__(parent)
        self.result = None
        self.title("Declare Your Task")
        self.geometry("320x170")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()
        self.configure(fg_color=C["bg"])

        ctk.CTkLabel(self, text="What are you working on?",
                     font=("Arial", 13), text_color=C["text"]).pack(pady=(18, 8))

        self.entry = ctk.CTkEntry(self, width=280, font=("Arial", 12),
                                  fg_color=C["dim"], text_color=C["text"],
                                  border_color=C["accent"])
        self.entry.pack(padx=16)
        if prefill:
            self.entry.insert(0, prefill)
            self.entry.select_range(0, "end")
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self._confirm())
        self.entry.bind("<Escape>", lambda e: self._skip())

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(pady=14)
        ctk.CTkButton(brow, text="Start", width=110,
                      fg_color=C["work"], hover_color="#a03030",
                      font=("Arial", 12, "bold"),
                      command=self._confirm).pack(side="left", padx=6)
        ctk.CTkButton(brow, text="Skip", width=90,
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"], font=("Arial", 11),
                      command=self._skip).pack(side="left", padx=6)

        self.wait_window()

    def _confirm(self):
        self.result = self.entry.get().strip() or None
        self.destroy()

    def _skip(self):
        self.result = None
        self.destroy()


# ── App ───────────────────────────────────────────────────────────────────────

class RazorTimer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg                  = self._load_config()
        self.collapsed            = False
        self._expanded_h          = 0
        self.running              = False
        self.phase                = "work"
        self.session_count        = 0
        self.time_remaining       = 0
        self.current_task         = ""
        self.current_task_time    = None
        self._last_incomplete     = ""
        self.session_log          = []
        self._last_export_count   = 0
        self._awaiting_completion = False
        self._setup_window()
        self._build_ui()
        self.reset_timer()
        self.after(100, self._cache_height)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        tmp = CONFIG_PATH.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self.cfg, f, indent=2)
        tmp.replace(CONFIG_PATH)

    def _cache_height(self):
        self.update_idletasks()
        self._expanded_h = self.winfo_height()

    # ── Window ────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Razor")
        self.overrideredirect(True)
        self.attributes("-topmost", self.cfg["always_on_top"])
        self.configure(fg_color=C["bg"])
        self.geometry(f"300x560+{self.cfg['window_x']}+{self.cfg['window_y']}")
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

        ctk.CTkButton(self.bar, text="×", width=26, height=24,
                      font=("Arial", 14), fg_color="transparent",
                      hover_color="#8b0000", text_color=C["text"],
                      command=self._quit).pack(side="right", padx=2, pady=4)

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

        self.lbl_phase = ctk.CTkLabel(self.body, text="WORK SESSION",
                                      font=("Courier New", 12, "bold"),
                                      text_color=C["work"])
        self.lbl_phase.pack(pady=(12, 0))

        self.lbl_time = ctk.CTkLabel(self.body, text="25:00",
                                     font=("Courier New", 52, "bold"),
                                     text_color=C["text"])
        self.lbl_time.pack(pady=(2, 6))

        # Declaration — large, readable, prominent
        self.lbl_declaration = ctk.CTkLabel(
            self.body, text="", wraplength=268,
            font=("Arial", 14), text_color=C["text"],
            justify="center"
        )
        self.lbl_declaration.pack(pady=(0, 6))

        # Normal controls row: START | RESET | ⏹ STOP | ⏭ SKIP
        self.controls_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self.controls_row.pack(pady=4)

        self.btn_start = ctk.CTkButton(
            self.controls_row, text="START", width=80,
            font=("Courier New", 12, "bold"),
            fg_color=C["work"], hover_color="#a03030",
            command=self.toggle_timer
        )
        self.btn_start.pack(side="left", padx=2)

        ctk.CTkButton(self.controls_row, text="RESET", width=62,
                      font=("Courier New", 11),
                      fg_color=C["accent"], hover_color="#1a4a8a",
                      command=self.reset_timer).pack(side="left", padx=2)

        ctk.CTkButton(self.controls_row, text="⏹", width=36,
                      font=("Arial", 13),
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"],
                      command=self.stop_session).pack(side="left", padx=2)

        ctk.CTkButton(self.controls_row, text="⏭", width=36,
                      font=("Arial", 13),
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"],
                      command=self.skip_phase).pack(side="left", padx=2)

        # Completion row (shown when work phase ends with a declared task)
        self.completion_row = ctk.CTkFrame(self.body, fg_color="transparent")

        ctk.CTkButton(self.completion_row, text="✓ DONE", width=120,
                      font=("Courier New", 11, "bold"),
                      fg_color=C["done"], hover_color="#307830",
                      command=lambda: self._log_completion(True)).pack(side="left", padx=4)

        ctk.CTkButton(self.completion_row, text="✗ NOT DONE", width=120,
                      font=("Courier New", 11),
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"],
                      command=lambda: self._log_completion(False)).pack(side="left", padx=4)

        self.lbl_session = ctk.CTkLabel(self.body, text="Session 0",
                                        font=("Courier New", 10),
                                        text_color=C["muted"])
        self.lbl_session.pack(pady=(8, 2))

        # Completed tasks list (hidden until first completion)
        self.completed_frame = ctk.CTkScrollableFrame(
            self.body, height=72, fg_color=C["dim"], corner_radius=6
        )

        # Mode selector
        mrow = ctk.CTkFrame(self.body, fg_color="transparent")
        mrow.pack(pady=4)
        self.mode_var = ctk.StringVar(value=self.cfg["mode"])
        for mode in self.cfg["modes"]:
            ctk.CTkRadioButton(mrow, text=mode, variable=self.mode_var, value=mode,
                               font=("Courier New", 10), text_color=C["text"],
                               command=self.change_mode).pack(side="left", padx=10)

        ctk.CTkFrame(self.body, fg_color=C["dim"], height=1).pack(fill="x", pady=6)

        self._build_settings()

        self.btn_export = ctk.CTkButton(
            self.body, text="Export Session →", width=200, height=28,
            font=("Courier New", 10), fg_color=C["accent"], hover_color="#1a4a8a",
            command=self.export_session
        )

    def _build_settings(self):
        srow = ctk.CTkFrame(self.body, fg_color="transparent")
        srow.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(srow, text="Sound:", font=("Courier New", 10),
                     text_color=C["muted"]).pack(side="left", padx=(4, 2))

        saved = self.cfg.get("sound", "beep")
        display = saved if saved in ("beep", "silent") else "custom..."
        self.sound_var = ctk.StringVar(value=display)

        ctk.CTkOptionMenu(srow, values=SOUND_OPTIONS, variable=self.sound_var,
                          width=100, height=24,
                          font=("Courier New", 10),
                          fg_color=C["accent"], button_color=C["dim"],
                          command=self._sound_changed).pack(side="left", padx=4)

        self.aot_var = ctk.BooleanVar(value=self.cfg["always_on_top"])
        ctk.CTkCheckBox(srow, text="Top", variable=self.aot_var,
                        font=("Courier New", 10), text_color=C["muted"],
                        width=50, command=self._toggle_aot).pack(side="right", padx=4)

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
        task_short = f" — {self.current_task[:20]}…" if len(self.current_task) > 20 else (f" — {self.current_task}" if self.current_task else "")
        self.lbl_bar_info.configure(
            text=f"| {label}  {m:02d}:{s:02d}{task_short}", text_color=color
        )

    # ── Declaration ───────────────────────────────────────────────────────────

    def _ask_declaration(self):
        dlg = _DeclarationDialog(self, prefill=self._last_incomplete)
        task = dlg.result
        if task:
            self.current_task      = task
            self.current_task_time = datetime.datetime.now()
            self._last_incomplete  = ""
            self._update_declaration_label()
        self._start_ticking()

    def _update_declaration_label(self):
        self.lbl_declaration.configure(
            text=f'"{self.current_task}"' if self.current_task else ""
        )

    # ── Timer ─────────────────────────────────────────────────────────────────

    def reset_timer(self):
        self.running = False
        self._awaiting_completion = False
        self.phase = "work"
        self.current_task = ""
        self.current_task_time = None
        work = self.cfg["modes"][self.cfg["mode"]]["work"]
        self.time_remaining = work * 60
        self._show_controls()
        self.btn_start.configure(text="START", fg_color=C["work"], hover_color="#a03030")
        self.lbl_phase.configure(text="WORK SESSION", text_color=C["work"])
        self.lbl_time.configure(text=self._fmt(self.time_remaining), text_color=C["text"])
        self._update_declaration_label()
        self._refresh_bar_info()

    def toggle_timer(self):
        if self.running:
            self.running = False
            self.btn_start.configure(text="RESUME")
        else:
            if self.phase == "work" and not self.current_task:
                self._ask_declaration()
            else:
                self._start_ticking()

    def _start_ticking(self):
        self.running = True
        self.btn_start.configure(text="PAUSE")
        threading.Thread(target=self._tick, daemon=True).start()

    def stop_session(self):
        """End current work phase early and trigger completion prompt."""
        if not self.running and not self.current_task:
            return
        self.running = False
        self.time_remaining = 0
        if self.phase == "work" and self.current_task:
            self._show_completion_buttons()
            secs = self.cfg["modes"][self.cfg["mode"]]["break"] * 60
            self.time_remaining = secs
            self._update_display()
        else:
            self.after(50, self._phase_done)

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
            if self.current_task:
                self._awaiting_completion = True
                self._show_completion_buttons()
                secs = self.cfg["modes"][self.cfg["mode"]]["break"] * 60
                self.time_remaining = secs
                self._update_display()
            else:
                self._transition_to_break()
        else:
            self._transition_to_work()

    def _transition_to_break(self):
        self.phase = "break"
        self.current_task = ""
        self.current_task_time = None
        secs = self.cfg["modes"][self.cfg["mode"]]["break"] * 60
        self.time_remaining = secs
        self._show_controls()
        self.lbl_phase.configure(text="BREAK", text_color=C["break"])
        self.lbl_time.configure(text_color=C["break"])
        self.btn_start.configure(text="START BREAK",
                                 fg_color=C["break"], hover_color="#307830")
        self._update_declaration_label()
        self._update_display()

    def _transition_to_work(self):
        self.phase = "work"
        secs = self.cfg["modes"][self.cfg["mode"]]["work"] * 60
        self.time_remaining = secs
        self._show_controls()
        self.lbl_phase.configure(text="WORK SESSION", text_color=C["work"])
        self.lbl_time.configure(text_color=C["text"])
        self.btn_start.configure(text="START",
                                 fg_color=C["work"], hover_color="#a03030")
        self._update_display()

    # ── Completion flow ───────────────────────────────────────────────────────

    def _show_completion_buttons(self):
        self.controls_row.pack_forget()
        self.completion_row.pack(pady=4)

    def _show_controls(self):
        self.completion_row.pack_forget()
        self.controls_row.pack(pady=4)
        self._awaiting_completion = False

    def _log_completion(self, completed: bool):
        entry = {
            "task":         self.current_task,
            "declared_at":  self.current_task_time.isoformat() if self.current_task_time else "",
            "completed_at": datetime.datetime.now().isoformat(),
            "completed":    completed,
        }
        self.session_log.append(entry)
        if not completed:
            self._last_incomplete = self.current_task
        else:
            self._last_incomplete = ""
        self._add_completed_item(entry)
        self._update_export_btn()
        self._transition_to_break()

    def _add_completed_item(self, entry: dict):
        icon  = "✓" if entry["completed"] else "✗"
        color = C["done"] if entry["completed"] else C["muted"]
        text  = f"{icon}  {entry['task']}"
        ctk.CTkLabel(
            self.completed_frame, text=text,
            font=("Arial", 11), text_color=color,
            anchor="w", justify="left"
        ).pack(fill="x", padx=6, pady=1)
        if len(self.session_log) == 1:
            self.completed_frame.pack(fill="x", pady=(2, 4))
            self.after(60, self._grow_for_list)

    def _grow_for_list(self):
        self.update_idletasks()
        req = self.winfo_reqheight()
        if req > self.winfo_height():
            self._expanded_h = req
            if not self.collapsed:
                self.geometry(f"300x{req}+{self.winfo_x()}+{self.winfo_y()}")

    # ── Export ────────────────────────────────────────────────────────────────

    def _has_unexported(self):
        return len(self.session_log) > self._last_export_count

    def _update_export_btn(self):
        if self._has_unexported():
            self.btn_export.pack(pady=(4, 6))
        else:
            self.btn_export.pack_forget()

    def export_session(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_name = f"razor_{ts}.md"
        path = filedialog.asksaveasfilename(
            title="Export Session",
            initialdir=str(LOG_DIR),
            initialfile=default_name,
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")]
        )
        if not path:
            return
        self._write_md(Path(path))
        self._last_export_count = len(self.session_log)
        self._update_export_btn()

    def _write_md(self, path: Path):
        now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        done  = [e for e in self.session_log if e["completed"]]
        undone = [e for e in self.session_log if not e["completed"]]
        lines = [
            f"# Razor Session — {now}\n",
            f"**{len(done)} completed / {len(self.session_log)} declared**\n",
        ]
        if done:
            lines.append("\n## Completed\n")
            for e in done:
                t = e["declared_at"][:16].replace("T", " ") if e["declared_at"] else "—"
                lines.append(f"- [x] {e['task']}  *(started {t})*")
        if undone:
            lines.append("\n## Not Completed\n")
            for e in undone:
                t = e["declared_at"][:16].replace("T", " ") if e["declared_at"] else "—"
                lines.append(f"- [ ] {e['task']}  *(started {t})*")
        path.write_text("\n".join(lines), encoding="utf-8")

    # ── Quit ──────────────────────────────────────────────────────────────────

    def _quit(self):
        if self._has_unexported():
            self._show_quit_dialog()
        else:
            self._close()

    def _show_quit_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Unsaved Session")
        dlg.geometry("280x130")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=C["bg"])
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Export session log before closing?",
                     font=("Arial", 11), text_color=C["text"],
                     wraplength=240).pack(pady=(16, 10))

        brow = ctk.CTkFrame(dlg, fg_color="transparent")
        brow.pack()

        def export_and_close():
            dlg.destroy()
            self.export_session()
            if not self._has_unexported():
                self._close()

        ctk.CTkButton(brow, text="Export & Close", width=110,
                      fg_color=C["done"], hover_color="#307830",
                      font=("Arial", 10),
                      command=export_and_close).pack(side="left", padx=4)

        ctk.CTkButton(brow, text="Close Anyway", width=110,
                      fg_color=C["dim"], hover_color="#3a3a6a",
                      text_color=C["muted"], font=("Arial", 10),
                      command=lambda: [dlg.destroy(), self._close()]).pack(side="left", padx=4)

    def _close(self):
        self.running = False
        self._save_config()
        self.destroy()

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


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    RazorTimer().mainloop()
