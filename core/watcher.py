"""
Filesystem watcher engine for SSSSSS.

Manages per-game watchdog Observers. Each game gets its own Observer
watching its save directory. When files change, the watcher triggers
backups via the backup engine.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from . import backup

logger = logging.getLogger(__name__)


class SaveEventHandler(FileSystemEventHandler):
    """Handles filesystem events in a game's save directory."""

    def __init__(self, game_id: str, save_root: Path, backup_dir: Path,
                 on_event: Optional[Callable[[str, str], None]] = None):
        """
        Args:
            game_id: Identifier for the game
            save_root: Root of the save directory being watched
            backup_dir: Where backups go for this game
            on_event: Callback(game_id, message) for UI updates
        """
        self.game_id = game_id
        self.save_root = save_root
        self.backup_dir = backup_dir
        self.on_event = on_event

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_save_change(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_save_change(event.src_path)

    def _handle_save_change(self, src_path: str) -> None:
        path = Path(src_path)
        result = backup.backup_file(path, self.backup_dir, self.save_root)
        if result and self.on_event:
            self.on_event(self.game_id, f"Backed up: {path.name}")

    # Intentionally NOT handling on_deleted — we never delete backups
    # when source files are deleted. That's the whole point.


class WatcherManager:
    """Manages per-game filesystem watchers."""

    def __init__(self, on_event: Optional[Callable[[str, str], None]] = None):
        self._observers: dict[str, Observer] = {}
        self._lock = threading.Lock()
        self.on_event = on_event

    def start_watching(self, game_id: str, save_path: Path,
                       backup_dir: Path) -> bool:
        """
        Start watching a game's save directory.

        Returns True if the watcher was started, False if already running
        or on error.
        """
        with self._lock:
            if game_id in self._observers:
                logger.debug(f"Already watching {game_id}")
                return False

            if not save_path.exists():
                logger.warning(
                    f"Cannot watch {game_id}: save path does not exist: {save_path}"
                )
                return False

            try:
                handler = SaveEventHandler(
                    game_id=game_id,
                    save_root=save_path,
                    backup_dir=backup_dir,
                    on_event=self.on_event,
                )

                observer = Observer()
                observer.schedule(handler, str(save_path), recursive=True)
                observer.start()

                self._observers[game_id] = observer
                logger.info(f"Started watching {game_id}: {save_path}")

                if self.on_event:
                    self.on_event(game_id, "Watcher started")

                return True
            except Exception as e:
                logger.error(f"Failed to start watcher for {game_id}: {e}")
                return False

    def stop_watching(self, game_id: str) -> bool:
        """Stop watching a game. Returns True if a watcher was stopped."""
        with self._lock:
            observer = self._observers.pop(game_id, None)
            if observer is None:
                return False

            try:
                observer.stop()
                observer.join(timeout=5)
                logger.info(f"Stopped watching {game_id}")

                if self.on_event:
                    self.on_event(game_id, "Watcher stopped")

                return True
            except Exception as e:
                logger.error(f"Error stopping watcher for {game_id}: {e}")
                return False

    def stop_all(self) -> None:
        """Stop all watchers."""
        with self._lock:
            for game_id, observer in self._observers.items():
                try:
                    observer.stop()
                    observer.join(timeout=5)
                    logger.info(f"Stopped watching {game_id}")
                except Exception as e:
                    logger.error(f"Error stopping watcher for {game_id}: {e}")
            self._observers.clear()

    def is_watching(self, game_id: str) -> bool:
        with self._lock:
            return game_id in self._observers

    def active_watchers(self) -> list[str]:
        with self._lock:
            return list(self._observers.keys())

    def active_count(self) -> int:
        with self._lock:
            return len(self._observers)
