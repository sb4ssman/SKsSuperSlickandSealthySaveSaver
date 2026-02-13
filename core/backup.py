"""
Backup engine for SSSSSS.

Handles creating timestamped snapshots of save directories, backup rotation
(pruning old snapshots), and optional ZIP compression.

Backup structure:
    {backup_root}/
        {game_id}/
            slot0000_20240115_103000/     # timestamped snapshot
                gameinfo.json
                ...
            slot0000_20240115_120000/
                gameinfo.json
                ...
"""

from __future__ import annotations

import logging
import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_snapshot(source_dir: Path, backup_dir: Path,
                    compress: bool = False) -> Optional[Path]:
    """
    Create a timestamped snapshot of a save directory.

    Args:
        source_dir: The save slot/folder to back up (e.g. .../SavedGames/slot0000)
        backup_dir: The game's backup directory (e.g. .../backups/subnautica)
        compress: Whether to create a ZIP instead of a directory copy

    Returns:
        Path to the created snapshot, or None on failure.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"{source_dir.name}_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if compress:
        snapshot_path = backup_dir / f"{snapshot_name}.zip"
        try:
            with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in source_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(source_dir))
            logger.info(f"Created compressed snapshot: {snapshot_path}")
            return snapshot_path
        except Exception as e:
            logger.error(f"Failed to create compressed snapshot of {source_dir}: {e}")
            return None
    else:
        snapshot_path = backup_dir / snapshot_name
        try:
            shutil.copytree(source_dir, snapshot_path)
            logger.info(f"Created snapshot: {snapshot_path}")
            return snapshot_path
        except Exception as e:
            logger.error(f"Failed to create snapshot of {source_dir}: {e}")
            return None


def backup_file(src_path: Path, backup_dir: Path,
                relative_to: Path) -> Optional[Path]:
    """
    Copy a single changed file into the current (latest) backup directory,
    preserving its relative path structure.

    This is used by the watcher for incremental file-level backups between
    full snapshots. Files are organized under a timestamped session directory.

    Args:
        src_path: The file that changed
        backup_dir: The game's backup directory
        relative_to: The save root to compute relative paths from

    Returns:
        Path to the copied file, or None on failure.
    """
    rel_path = src_path.relative_to(relative_to)
    dest_path = backup_dir / "latest" / rel_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            shutil.copy2(src_path, dest_path)
            logger.info(f"Backed up file: {src_path} -> {dest_path}")
            return dest_path
        except PermissionError:
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            else:
                logger.error(
                    f"Failed to backup {src_path} after {max_attempts} attempts"
                )
                return None
        except Exception as e:
            logger.error(f"Failed to backup {src_path}: {e}")
            return None

    return None


def rotate_backups(backup_dir: Path, max_count: int) -> int:
    """
    Prune old backups, keeping only the most recent `max_count`.

    Deletes the oldest snapshots (by name, which embeds timestamp).
    Returns the number of snapshots deleted.
    """
    if max_count <= 0:
        return 0

    snapshots = sorted(get_snapshots(backup_dir))

    deleted = 0
    while len(snapshots) > max_count:
        oldest = snapshots.pop(0)
        try:
            if oldest.is_dir():
                shutil.rmtree(oldest)
            else:
                oldest.unlink()
            logger.info(f"Pruned old backup: {oldest}")
            deleted += 1
        except Exception as e:
            logger.error(f"Failed to prune {oldest}: {e}")

    return deleted


def get_snapshots(backup_dir: Path) -> list[Path]:
    """
    List all snapshots in a backup directory, sorted oldest first.

    Snapshots are directories or ZIP files matching the naming pattern.
    """
    if not backup_dir.exists():
        return []

    snapshots = []
    for item in backup_dir.iterdir():
        # Skip the "latest" incremental directory
        if item.name == "latest":
            continue
        if item.is_dir() or (item.is_file() and item.suffix == ".zip"):
            snapshots.append(item)

    return sorted(snapshots, key=lambda p: p.name)


def get_backup_size(backup_dir: Path) -> int:
    """Get total size of all backups in bytes."""
    total = 0
    if not backup_dir.exists():
        return 0
    for f in backup_dir.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
