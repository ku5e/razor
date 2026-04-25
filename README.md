# Razor

Floating Pomodoro timer built for ADHD-pattern focus sessions.

Part of the **Anchor** project — AI-powered body doubling tools for people who work better with external accountability.

---

## What It Does

- Floating, always-on-top widget
- Collapses to a title bar showing phase and time remaining
- 25/5 and 50/10 modes
- Skip button to advance the current phase
- Alert sound on phase end: built-in beep, silent, or any WAV/MP3 from your machine
- Position and settings persist between sessions

## The Loop

1. Declare your task out loud (or to an AI)
2. Start a session
3. Work — no switching, no checking, nothing else
4. Report back when the timer ends

Declaring the task before starting is the whole thing. The timer enforces the interval. The report closes the loop.

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

Body doubling — working in the presence of another person — is one of the most reliable focus techniques for ADHD-pattern brains. Most people don't have a body double available on demand.

Razor is the timer half of an AI body double loop. You declare your intention, the timer holds the interval, and you report back. The accountability is real because you said what you were going to do before you started.

---

## Support

If Razor is useful to you, consider supporting continued development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/ku5e)

---

## License

MIT
