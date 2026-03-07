"""
Settings management for SSSSSS.

Handles application settings and per-game configuration using dataclasses
with JSON persistence. Settings file lives next to the application.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Per-game configuration set by the user."""
    game_id: str
    save_path: Optional[str] = None          # Resolved save folder path
    backup_dir: Optional[str] = None         # Per-game override (None = use default)
    watch_mode: str = "always"               # "always" | "while_running" | "disabled"
    max_backups: Optional[int] = None        # Per-game override (None = use default)
    enabled: bool = True

    def effective_backup_dir(self, default_root: Path) -> Path:
        """Return the backup directory for this game, falling back to default."""
        if self.backup_dir:
            return Path(self.backup_dir)
        return default_root / self.game_id

    def effective_max_backups(self, default: int) -> int:
        """Return max backups for this game, falling back to default."""
        if self.max_backups is not None:
            return self.max_backups
        return default


@dataclass
class AppSettings:
    """Application-wide settings."""
    backup_root: str = ""                    # Centralized backup location
    default_max_backups: int = 50            # Default per-game backup retention
    compress_backups: bool = False           # ZIP compression
    start_minimized: bool = True             # Start in tray without status window
    check_process: bool = True              # Monitor game processes
    games: dict[str, dict] = field(default_factory=dict)  # game_id -> GameConfig as dict

    def get_backup_root(self, app_dir: Path) -> Path:
        """Return backup root, defaulting to {app_dir}/backups/."""
        if self.backup_root:
            return Path(self.backup_root)
        return app_dir / "backups"

    def get_game_config(self, game_id: str) -> GameConfig:
        """Get or create a GameConfig for a game."""
        if game_id in self.games:
            data = self.games[game_id]
            return GameConfig(game_id=game_id, **data)
        return GameConfig(game_id=game_id)

    def set_game_config(self, config: GameConfig) -> None:
        """Store a GameConfig back into settings."""
        d = asdict(config)
        d.pop("game_id")
        self.games[config.game_id] = d


class SettingsManager:
    """Loads and saves AppSettings to a JSON file."""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.settings_file = app_dir / "settings.json"
        self.settings = self._load()

    def _load(self) -> AppSettings:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                return AppSettings(**data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.error(f"Error loading settings: {e}. Using defaults.")
        return AppSettings()

    def save(self) -> None:
        try:
            with open(self.settings_file, "w") as f:
                json.dump(asdict(self.settings), f, indent=4)
            logger.info("Settings saved")
        except IOError as e:
            logger.error(f"Error saving settings: {e}")

    @property
    def backup_root(self) -> Path:
        return self.settings.get_backup_root(self.app_dir)
