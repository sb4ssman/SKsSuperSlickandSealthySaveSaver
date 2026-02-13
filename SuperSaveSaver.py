"""
SK's Super Slick and Stealthy Save Saver — Application Core

Wires together all subsystems: config, registry, detector, watcher,
backup, restore, tray icon, and status window.
"""

from __future__ import annotations

import argparse
import logging
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Optional

import pystray
from pystray import MenuItem
from PIL import ImageTk

from core import backup
from core.config import SettingsManager, GameConfig
from core.registry import GameRegistry
from core.detector import find_steam_libraries, find_steam_game_install, probe_save_paths
from core.watcher import WatcherManager
from ui.tray import TrayIcon
from ui.status_window import StatusWindow

VERSION = "2.0.0"

logger = logging.getLogger(__name__)


class SuperSaveSaver:
    """Main application class. Owns all subsystems."""

    def __init__(self, silent: bool = False):
        self.silent = silent
        self.app_dir = Path(__file__).parent.resolve()

        # Set up logging
        log_file = self.app_dir / "sssss.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )

        # Global exception handler
        sys.excepthook = lambda et, ev, tb: logging.error(
            "Uncaught exception", exc_info=(et, ev, tb),
        )

        logger.info(f"Starting SSSSSS v{VERSION}")

        # Subsystems
        self.settings_mgr = SettingsManager(self.app_dir)
        self.registry = GameRegistry()
        self.event_queue: queue.Queue = queue.Queue()

        # Watcher manager with event callback
        self.watcher = WatcherManager(on_event=self._on_watcher_event)

        # Tkinter root (hidden)
        self.root = tk.Tk()
        self.root.withdraw()

        # Window icon
        self._set_window_icon()

        # Style
        try:
            from tkinter import ttk
            ttk.Style().theme_use("xpnative")
        except Exception:
            pass

        # UI
        self.status_window = StatusWindow(self)
        self.tray: Optional[TrayIcon] = None

        # Event processing
        self.root.after(100, self._process_events)

    def start(self) -> None:
        """Initialize and run the application."""
        try:
            # Detect games if first run
            if not self.settings_mgr.settings.games:
                logger.info("First run — detecting games")
                self._detect_games()
            else:
                logger.info(
                    f"Loaded {len(self.settings_mgr.settings.games)} configured games"
                )

            # Start watchers for enabled games
            self._start_configured_watchers()

            # Create tray icon
            self.tray = TrayIcon(
                on_show_status=self._show_status,
                on_quit=self.quit,
                get_game_menu_items=self._build_game_menu_items,
                get_active_count=self.watcher.active_count,
            )
            self.tray.start()

            # Show status window unless silent
            if not self.silent:
                self.root.after(100, self._show_status)

            logger.info("Startup complete")
            self.root.mainloop()

        except Exception as e:
            logger.error(f"Fatal error during startup: {e}")
            if self.tray:
                self.tray.stop()
            raise

    def quit(self) -> None:
        """Clean shutdown."""
        logger.info("Shutting down")
        self.watcher.stop_all()
        if self.tray:
            self.tray.stop()
        self.root.quit()
        self.root.destroy()

    def save_now(self, game_id: str) -> None:
        """Manually trigger a full snapshot for a game."""
        config = self.settings_mgr.settings.get_game_config(game_id)
        if not config.save_path:
            messagebox.showerror("Error", f"No save path configured for {game_id}")
            return

        save_path = Path(config.save_path)
        if not save_path.exists():
            messagebox.showerror("Error", f"Save path does not exist: {save_path}")
            return

        backup_dir = config.effective_backup_dir(self.settings_mgr.backup_root)
        game_def = self.registry.get(game_id)
        pattern = game_def.save_pattern if game_def else "*"
        compress = self.settings_mgr.settings.compress_backups

        saved = []
        for item in save_path.iterdir():
            if item.is_dir() and item.match(pattern):
                result = backup.create_snapshot(item, backup_dir, compress)
                if result:
                    saved.append(item.name)

        # If no subdirs matched pattern, snapshot the whole save dir
        if not saved:
            result = backup.create_snapshot(save_path, backup_dir, compress)
            if result:
                saved.append(save_path.name)

        # Rotate
        max_b = config.effective_max_backups(
            self.settings_mgr.settings.default_max_backups
        )
        backup.rotate_backups(backup_dir, max_b)

        if saved:
            msg = f"Backed up: {', '.join(saved)}"
            logger.info(f"Manual save for {game_id}: {msg}")
            self.status_window.log(msg)
            self.status_window.refresh_game(game_id)
            messagebox.showinfo("Backup Complete", msg)
        else:
            messagebox.showwarning("Backup", "No save files found to back up.")

    # --- Internal ---

    def _set_window_icon(self) -> None:
        ico_path = self.app_dir / "app_icon.ico"
        if sys.platform == "win32" and ico_path.exists():
            try:
                self.root.iconbitmap(str(ico_path))
            except Exception:
                pass

    def _show_status(self) -> None:
        self.status_window.show()

    def _detect_games(self) -> None:
        """Auto-detect installed games and configure them."""
        steam_libs = find_steam_libraries()
        found = 0

        for game_id, game_def in self.registry.all_games().items():
            install_dir = None

            # Try Steam detection
            if game_def.steam_id:
                install_dir = find_steam_game_install(
                    game_def.steam_id, steam_libs,
                )

            # Probe save paths
            existing_paths = probe_save_paths(
                game_def.save_paths, install_dir,
            )

            if existing_paths:
                save_path = str(existing_paths[0])
                config = GameConfig(
                    game_id=game_id,
                    save_path=save_path,
                    enabled=True,
                )
                self.settings_mgr.settings.set_game_config(config)
                found += 1
                logger.info(f"Detected {game_def.name}: {save_path}")

        self.settings_mgr.save()
        logger.info(f"Game detection complete: {found} games found")

    def _start_configured_watchers(self) -> None:
        """Start filesystem watchers for all enabled games."""
        for game_id, game_data in self.settings_mgr.settings.games.items():
            config = self.settings_mgr.settings.get_game_config(game_id)
            if not config.enabled or config.watch_mode == "disabled":
                continue
            if not config.save_path:
                continue

            save_path = Path(config.save_path)
            if not save_path.exists():
                logger.warning(f"Save path missing for {game_id}: {save_path}")
                continue

            backup_dir = config.effective_backup_dir(self.settings_mgr.backup_root)
            self.watcher.start_watching(game_id, save_path, backup_dir)

    def _on_watcher_event(self, game_id: str, message: str) -> None:
        """Callback from watcher threads — queues events for the UI thread."""
        self.event_queue.put((game_id, message))

    def _process_events(self) -> None:
        """Process queued events on the tkinter main thread."""
        try:
            while True:
                game_id, message = self.event_queue.get_nowait()
                self.status_window.log(f"[{game_id}] {message}")
                self.status_window.refresh_game(game_id)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_events)

    def _build_game_menu_items(self) -> list[MenuItem]:
        """Build per-game menu items for the tray icon."""
        items = []
        for game_id, game_data in self.settings_mgr.settings.games.items():
            game_def = self.registry.get(game_id)
            name = game_def.name if game_def else game_id
            is_watching = self.watcher.is_watching(game_id)

            status = "Watching" if is_watching else "Idle"
            items.append(
                MenuItem(
                    f"{name} [{status}]",
                    pystray.Menu(
                        MenuItem(
                            "Save Now",
                            lambda _, gid=game_id: self.root.after(
                                0, lambda: self.save_now(gid),
                            ),
                        ),
                        MenuItem(
                            "Open Save Folder",
                            lambda _, gid=game_id: self._open_save_folder(gid),
                        ),
                    ),
                )
            )
        return items

    def _open_save_folder(self, game_id: str) -> None:
        config = self.settings_mgr.settings.get_game_config(game_id)
        if config.save_path and Path(config.save_path).exists():
            import os
            os.startfile(config.save_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SK's Super Slick and Stealthy Save Saver",
    )
    parser.add_argument(
        "--silent", action="store_true",
        help="Start minimized to tray without showing the status window",
    )
    args = parser.parse_args()

    app = SuperSaveSaver(silent=args.silent)
    try:
        app.start()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        if not args.silent:
            messagebox.showerror(
                "Fatal Error",
                f"A fatal error occurred: {e}\nCheck sssss.log for details.",
            )
        sys.exit(1)
