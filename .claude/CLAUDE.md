# CLAUDE.md - Project Directives

## Project Identity

**SK's Super Slick and Stealthy Save Saver (SSSSSS)**
A Python system-tray application that automatically backs up video game save files using real-time filesystem watching. Originally built for Subnautica, expanding to support any game.

- **Author**: sb4ssman
- **Language**: Python (tkinter, pystray, watchdog, Pillow, pywin32)
- **Platform**: Windows (primary)

## On Every Session Start

1. **Check your working notes first**: Read `_claude_notes/claude_notes.md` for current status, active tasks, and context from previous sessions.
2. **Run the folder structure tool**: Execute `python _claude_notes/_claude_tools/generate_folder_structure.py` and read the output at `_claude_notes/_claude_outputs/folder_structure.md` to get a clear overview of the current project structure.
3. **Check the work log**: Read the tail of `_claude_notes/work_log.md` for the most recent completed work (newest entries are at the END of the file).

## Notes System

### `_claude_notes/claude_notes.md` — Working Notes (ACTIVE)
- Current state of work in progress
- Active task checklists (use `- [ ]` / `- [x]` format)
- Decisions pending user input
- Known issues being tracked
- Keep this file CLEAN and CURRENT — remove stale items, update descriptions as work progresses

### `_claude_notes/work_log.md` — Completed Work Log (APPEND-ONLY)
- When a task or milestone is completed to the user's satisfaction, move it from working notes to here
- **Always append new entries at the END of the file** (newest last)
- When reading for context, read the TAIL of this file for the most recent work
- Format each entry with a date header and brief summary of what was done and why

### `_claude_notes/_claude_tools/` — Utility Scripts
- `generate_folder_structure.py` — Generates ASCII folder tree to `_claude_outputs/folder_structure.md`

### `_claude_notes/_claude_outputs/` — Tool Output (gitignored, ephemeral)
- Output from tools; regenerated on demand

## Architecture Notes

- The main application class is `SkSubnauticaSaveSaver` in `SubnauticaSaveSaver.py`
- `TrayHelper` manages the pystray system tray icon lifecycle
- `SaveHandler` is the watchdog `FileSystemEventHandler` that triggers backups
- `ToolTips.py` is a standalone reusable tkinter tooltip widget

## Code Style

- Use `pathlib.Path` over `os.path` for new code
- Type hints on new functions
- Dataclasses for structured data (settings, game profiles)
- Keep the tool lightweight — it's a tray app, not a framework
