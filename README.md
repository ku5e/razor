# Razor

Floating Pomodoro timer built for ADHD-pattern focus sessions. Part of the **Anchor** project: AI-powered body doubling tools for people who work better with external accountability.

---

## The Loop

1. Hit **START** and declare what you are working on
2. Work for 25 minutes, no other windows, no other tasks
3. Timer ends: mark it **Done** or **Not Done**
4. Report back to your AI body double
5. Repeat

Declaring the task before starting is the mechanism. The timer enforces the interval. The report closes the loop.

---

## What It Does

**Timer**
- Floating, always-on-top widget that stays visible over your work
- Collapses to a slim title bar showing phase, time remaining, and your declared task
- 25/5 and 50/10 modes
- START / PAUSE / RESET / STOP / SKIP controls
- Alert sound on phase end: built-in beep, silent, or any WAV/MP3 from your machine

**Declare, work, report**
- Declaration prompt before every work session
- If the last task was not completed, it pre-fills so you can carry it forward or replace it
- Declared task displayed in the widget during the session
- Work phase ends with a Done / Not Done prompt, not an automatic transition
- Completed and incomplete tasks listed in the widget as the session builds

**Export**
- Export Session button appears once tasks are logged
- Saves a dated Markdown file to `~/Documents/razor/`, named by date and time: `razor_2026-04-25_14-30.md`
- Completed tasks marked `[x]`, incomplete marked `[ ]`, each with start time
- Closing with unexported tasks prompts: Export and Close, or Close Anyway

**Settings persist**
- Window position, mode, sound, and always-on-top preference save automatically
- Config stored in `AppData/Local/razor/` on Windows and `~/.config/razor/` on macOS, separate from the project folder

---

## Install

```bash
pip install -r requirements.txt
python timer.py
```

**Requirements:** Python 3.10+, Windows or macOS.

## Build Standalone Executable

**Windows:**
```
build_windows.bat
```
Output: `dist\razor\razor.exe`

**macOS:**
```bash
chmod +x build_mac.sh
./build_mac.sh
```
Output: `dist/Razor.app`

---

## Why This Exists

Body doubling is working in the presence of another person. It is one of the most consistent focus techniques for ADHD-pattern brains, and most people do not have a body double available when they need one.

Razor is the timer half of an AI body double loop. You declare your task, the timer holds the interval, and you report back. You said what you were going to do before you started. That is the accountability.

---

## Support

If Razor is useful to you, consider sponsoring continued development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?logo=github)](https://github.com/sponsors/ku5e)

---

## License

MIT
