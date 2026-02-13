# Work Log — SK's Super Slick and Stealthy Save Saver

Completed work entries. Newest at the bottom. Read the tail for most recent work.

---

## 2026-02-12 — Initial Assessment & Research

**What was done:**
- Full codebase review of all project files (SubnauticaSaveSaver.py, ToolTips.py, autoSSSSS.bat, requirements.txt, .gitignore)
- Senior engineer assessment identifying 10 bugs, architectural issues (god class, threading, dead code), and strengths
- Competitive landscape research: analyzed 19 comparable tools across Subnautica-specific, general-purpose, and cloud sync categories
- Deep technical analysis of Ludusavi: manifest format, schema, path placeholders, CLI, backup structure, API modes, PCGamingWiki scraping pipeline
- Confirmed SSSSSS has a unique competitive position: only tool combining real-time filesystem watching + external backup + zero-interaction operation
- Decision: evolve from Subnautica-only to general-purpose game save watcher ("SK's Super Slick and Stealthy Save Saver")
- Decision: use Ludusavi manifest as a reference, not a runtime dependency — build lightweight game registry instead

**What was set up:**
- Fixed `_claude_notes/_claude_tools/generate_folder_structure.py` (was referencing "Windopener" from another project)
- Created `.claude/CLAUDE.md` with project directives and session-start procedures
- Created `_claude_notes/claude_notes.md` for active working notes
- Created `_claude_notes/work_log.md` (this file)

---

## 2026-02-12 — Full Package Scaffold (v2.0)

**What was done:**
- Archived original v1.0 files to `archive/` (SubnauticaSaveSaver.py, ToolTips.py, autoSSSSS.bat)
- Built complete `sssss/` package from scratch with clean module separation:
  - `config.py` — `AppSettings` + `GameConfig` dataclasses with JSON persistence, centralized backup root with per-game override
  - `registry.py` — `GameDefinition` dataclass, placeholder resolution, loads shipped `games/manifest.json`
  - `backup.py` — Timestamped snapshots (dir copy or ZIP), rotation/pruning, file-level incremental backups, size formatting
  - `watcher.py` — `WatcherManager` with per-game observers, thread-safe start/stop, event callbacks. Intentionally ignores on_deleted (critical bug fix from v1.0)
  - `restore.py` — Restore from snapshots with automatic safety backup of current save before overwriting
  - `detector.py` — Steam library discovery (registry + libraryfolders.vdf parsing), appmanifest parsing, save path probing, process detection via ctypes (no psutil)
  - `ui/tray.py` — Clean TrayIcon with Win32 double-click, status indicator (green/orange/red), per-game submenus
  - `ui/status_window.py` — Tabbed per-game UI with path settings, backup treeview, restore controls, global settings, log viewer
  - `ui/tooltips.py` — Ported ToolTip widget
  - `SuperSaveSaver.py` — App lifecycle wiring all subsystems, auto-detection on first run, event queue for thread-safe UI updates
  - `__main__.py` — Entry point (`python -m sssss --silent`)
- Created `games/manifest.json` with 15 game definitions: Subnautica, Subnautica Below Zero, Elden Ring, Dark Souls III, Valheim, Stardew Valley, Satisfactory, Cyberpunk 2077, No Man's Sky, The Forest, Sons of the Forest, Baldur's Gate 3, Terraria, Palworld, Minecraft Java
- All original v1.0 bugs addressed in new architecture (no on_deleted propagation, no dead code, no god class, proper timestamped snapshots, thread-safe observer management)
