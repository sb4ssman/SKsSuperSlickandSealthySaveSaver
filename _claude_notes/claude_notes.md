# Working Notes — SK's Super Slick and Stealthy Save Saver

## Current Status

**Initial scaffold complete.** All modules written. The new `sssss/` package has been built from the ground up. Original files preserved in `archive/`. Next step: test, debug, iterate with user.

## Project Structure

```
sssss/                    # Main package
    __init__.py           # VERSION = "2.0.0"
    __main__.py           # python -m sssss (entry point)
    SuperSaveSaver.py     # App lifecycle, wires all subsystems together
    config.py             # AppSettings + GameConfig dataclasses, JSON persistence
    registry.py           # GameDefinition dataclass, loads games/manifest.json
    detector.py           # Steam library parsing, save path probing, process detection
    watcher.py            # WatcherManager + SaveEventHandler (per-game watchdog observers)
    backup.py             # Timestamped snapshots, rotation/pruning, ZIP compression
    restore.py            # Restore from snapshots with safety backup
    ui/
        tray.py           # TrayIcon with double-click support, status indicator
        status_window.py  # Tabbed game settings, backup lists, log viewer
        tooltips.py       # ToolTip widget (ported from original)
    games/
        manifest.json     # 15 game definitions (Subnautica, Elden Ring, Valheim, etc.)
archive/                  # Original v1.0 files preserved
```

## Active Tasks

- [ ] Test the app end-to-end (python -m sssss)
- [ ] Fix any import/runtime issues from the initial scaffold
- [ ] Update requirements.txt to actual dependencies only
- [ ] Update autoSSSSS.bat to use %~dp0 and new package structure
- [ ] Update README.md for new project name and structure
- [ ] Consider: "Add Game" UI flow for games not in manifest

## Key Decisions Made

- **Name**: SK's Super Slick and Stealthy Save Saver (6 S's: SSSSSS)
- **Backup centralization**: All backups default to `{app_dir}/backups/{game_id}/`. User can change root location. Per-game override available.
- **No Ludusavi runtime dependency**: Own lightweight JSON manifest, Ludusavi manifest used as reference only.
- **No on_deleted propagation**: Watcher intentionally ignores file deletions — backups are NEVER deleted when source files are deleted.
- **Timestamped snapshots on every backup**: Both manual and automatic backups create timestamped copies.
- **Backup rotation**: Configurable max backups per game (default 50), auto-prunes oldest.
- **Process detection via ctypes**: No psutil dependency — uses Windows Toolhelp32 API directly.
- **Steam detection via VDF parsing**: Reads libraryfolders.vdf + appmanifest ACF files, no Steam API dependency.

## Future Thoughts (not for now)

- Timeline/rewind view for restore UI (inspired by Steamback)
- Cloud sync support (Google Drive / OneDrive)
- Cross-platform support (Linux/Mac — would need platform abstraction for process detection)
- Import from Ludusavi manifest command
- Process-aware watching (only watch while game is running)
