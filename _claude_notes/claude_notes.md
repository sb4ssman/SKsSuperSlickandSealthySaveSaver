# Working Notes — SK's Super Slick and Stealthy Save Saver

## Current Status

**Project reorganized and setup system enhanced.** Application code moved to `App/` folder, assets to `Assets/`. Setup script creates launcher bat and handles startup integration. Currently fixing setup script issues.

## Project Structure

```
App/                      # Application code
    core/                 # Core functionality (backup, watcher, detector, etc.)
    ui/                   # UI components (tray, status window, tooltips)
    SuperSaveSaver.py     # Main entry point
Assets/                   # Assets (icons, etc.)
    app_icon.ico
build_scripts/            # Build/setup scripts
    setup.py
archive/                  # Original v1.0 files preserved
```

## Active Tasks

- [ ] Test the app end-to-end
- [ ] Update README.md for new project structure
- [ ] Monitor setup script behavior in Cursor's batch runner (input handling may need further refinement)

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
