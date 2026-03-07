"""
Game registry for SSSSSS.

Loads game definitions from the shipped manifest (games/manifest.json).
Each game definition describes where its save files live, what process
it runs as, and how to identify it.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path placeholders resolved at runtime
_PLACEHOLDERS = {
    "{home}": Path.home(),
    "{appdata}": Path(os.environ.get("APPDATA", "")),
    "{localappdata}": Path(os.environ.get("LOCALAPPDATA", "")),
    "{localappdata_low}": Path.home() / "AppData" / "LocalLow",
    "{documents}": Path.home() / "Documents",
    "{public}": Path(os.environ.get("PUBLIC", "C:/Users/Public")),
    "{programdata}": Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")),
}


@dataclass
class GameDefinition:
    """A game's save file profile from the registry."""
    game_id: str
    name: str
    process: Optional[str] = None            # e.g. "Subnautica.exe"
    save_paths: list[str] = field(default_factory=list)  # Path templates
    save_pattern: str = "*"                  # Glob for save dirs/files within save_paths
    steam_id: Optional[int] = None
    notes: Optional[str] = None

    def resolve_save_paths(self, install_dir: Optional[Path] = None) -> list[Path]:
        """Resolve placeholder paths to actual filesystem paths that exist."""
        resolved = []
        for template in self.save_paths:
            path_str = template

            # Resolve install_dir placeholder
            if "{install_dir}" in path_str:
                if install_dir is None:
                    continue
                path_str = path_str.replace("{install_dir}", str(install_dir))

            # Resolve environment-based placeholders
            for placeholder, value in _PLACEHOLDERS.items():
                if placeholder in path_str:
                    path_str = path_str.replace(placeholder, str(value))

            path = Path(path_str)
            if path.exists():
                resolved.append(path)

            logger.debug(f"Resolved '{template}' -> '{path}' (exists={path.exists()})")

        return resolved


class GameRegistry:
    """Loads and manages game definitions."""

    def __init__(self):
        self._games: dict[str, GameDefinition] = {}
        self._load_builtin_manifest()

    def _load_builtin_manifest(self) -> None:
        """Load the shipped manifest.json."""
        manifest_path = Path(__file__).parent / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"Built-in manifest not found: {manifest_path}")
            return

        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)

            for game_id, entry in data.items():
                self._games[game_id] = GameDefinition(game_id=game_id, **entry)

            logger.info(f"Loaded {len(self._games)} game definitions from manifest")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.error(f"Error loading manifest: {e}")

    def load_custom_manifest(self, path: Path) -> None:
        """Load additional game definitions from a user-provided file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)

            count = 0
            for game_id, entry in data.items():
                self._games[game_id] = GameDefinition(game_id=game_id, **entry)
                count += 1

            logger.info(f"Loaded {count} custom game definitions from {path}")
        except (json.JSONDecodeError, TypeError, KeyError, IOError) as e:
            logger.error(f"Error loading custom manifest {path}: {e}")

    def get(self, game_id: str) -> Optional[GameDefinition]:
        return self._games.get(game_id)

    def all_games(self) -> dict[str, GameDefinition]:
        return dict(self._games)

    def find_by_steam_id(self, steam_id: int) -> Optional[GameDefinition]:
        for game in self._games.values():
            if game.steam_id == steam_id:
                return game
        return None

    def find_by_process(self, process_name: str) -> Optional[GameDefinition]:
        proc_lower = process_name.lower()
        for game in self._games.values():
            if game.process and game.process.lower() == proc_lower:
                return game
        return None

    def add_custom_game(self, game_id: str, name: str, save_path: str,
                        process: Optional[str] = None,
                        save_pattern: str = "*") -> GameDefinition:
        """Add a user-defined game at runtime."""
        game = GameDefinition(
            game_id=game_id,
            name=name,
            save_paths=[save_path],
            process=process,
            save_pattern=save_pattern,
        )
        self._games[game_id] = game
        logger.info(f"Added custom game: {name} ({game_id})")
        return game
