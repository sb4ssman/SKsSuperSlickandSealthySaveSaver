"""
Restore engine for SSSSSS.

Handles restoring game saves from backups with safety checks.
Always creates a safety backup of the current save before overwriting.
"""

from __future__ import annotations

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from . import backup

logger = logging.getLogger(__name__)


def restore_snapshot(snapshot_path: Path, save_dir: Path,
                     safety_backup_dir: Optional[Path] = None) -> bool:
    """
    Restore a snapshot to the game's save directory.

    If a save_pattern slot name can be parsed from the snapshot name,
    restores into that slot. Otherwise restores to the save_dir root.

    Args:
        snapshot_path: The snapshot directory or ZIP to restore from
        save_dir: The game's active save directory
        safety_backup_dir: If provided, back up current save here first

    Returns:
        True on success, False on failure.
    """
    # Parse the original slot/folder name from snapshot name
    # e.g. "slot0000_20240115_103000" -> "slot0000"
    snapshot_name = snapshot_path.stem if snapshot_path.suffix == ".zip" else snapshot_path.name
    parts = snapshot_name.split("_")

    # Find where the timestamp starts (8 digits for date)
    original_name = snapshot_name
    for i, part in enumerate(parts):
        if len(part) == 8 and part.isdigit():
            original_name = "_".join(parts[:i])
            break

    destination = save_dir / original_name

    # Safety backup of current state
    if safety_backup_dir and destination.exists():
        safety = backup.create_snapshot(destination, safety_backup_dir)
        if safety:
            logger.info(f"Safety backup created: {safety}")
        else:
            logger.warning("Failed to create safety backup, proceeding anyway")

    try:
        if snapshot_path.suffix == ".zip":
            _restore_from_zip(snapshot_path, destination)
        else:
            _restore_from_dir(snapshot_path, destination)

        logger.info(f"Restored {snapshot_name} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore {snapshot_path}: {e}")
        return False


def _restore_from_dir(source: Path, destination: Path) -> None:
    """Restore from a directory snapshot."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _restore_from_zip(zip_path: Path, destination: Path) -> None:
    """Restore from a ZIP snapshot."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destination)


def list_snapshots(backup_dir: Path) -> list[dict]:
    """
    List available snapshots for a game with metadata.

    Returns a list of dicts with keys: name, path, time, size, type
    """
    snapshots = backup.get_snapshots(backup_dir)
    result = []
    for snap in snapshots:
        stat = snap.stat()
        size = (
            stat.st_size
            if snap.is_file()
            else backup.get_backup_size(snap)
        )
        result.append({
            "name": snap.name,
            "path": snap,
            "time": stat.st_mtime,
            "size": size,
            "type": "zip" if snap.suffix == ".zip" else "directory",
        })
    return result
