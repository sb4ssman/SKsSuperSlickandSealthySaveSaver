"""
Game detection for SSSSSS.

Finds installed games by:
1. Parsing Steam library folders (libraryfolders.vdf)
2. Probing known save paths for existence
3. Checking running processes (for process-aware watching)
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
import struct
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_steam_libraries() -> list[Path]:
    """
    Find all Steam library folders on this system.

    Parses Steam's libraryfolders.vdf to find all library paths.
    Returns a list of library root paths (each containing a steamapps/ dir).
    """
    steam_paths = _find_steam_install()
    if not steam_paths:
        logger.info("Steam installation not found")
        return []

    libraries = []
    for steam_path in steam_paths:
        vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
        if vdf_path.exists():
            libraries.extend(_parse_library_folders_vdf(vdf_path))
            break

    if not libraries and steam_paths:
        # Fallback: the Steam install itself is always a library
        default = steam_paths[0] / "steamapps"
        if default.exists():
            libraries.append(default)

    logger.info(f"Found {len(libraries)} Steam libraries: {libraries}")
    return libraries


def _find_steam_install() -> list[Path]:
    """Find Steam installation directory from common locations."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Steam",
        Path.home() / "Steam",
    ]

    # Also check registry
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            candidates.insert(0, Path(install_path))
    except (ImportError, OSError):
        pass

    return [p for p in candidates if p.exists()]


def _parse_library_folders_vdf(vdf_path: Path) -> list[Path]:
    """
    Parse libraryfolders.vdf to extract library paths.

    The VDF format is Valve's key-value format. We do simple regex parsing
    rather than pulling in a VDF library dependency.
    """
    libraries = []
    try:
        content = vdf_path.read_text(encoding="utf-8", errors="replace")
        # Match "path" values in the VDF
        for match in re.finditer(r'"path"\s+"([^"]+)"', content):
            lib_path = Path(match.group(1).replace("\\\\", "\\"))
            steamapps = lib_path / "steamapps"
            if steamapps.exists():
                libraries.append(steamapps)
    except Exception as e:
        logger.error(f"Error parsing {vdf_path}: {e}")

    return libraries


def find_steam_game_install(steam_id: int,
                            libraries: Optional[list[Path]] = None) -> Optional[Path]:
    """
    Find a game's install directory by its Steam app ID.

    Checks each Steam library's appmanifest files for a matching app ID
    and returns the install directory path.
    """
    if libraries is None:
        libraries = find_steam_libraries()

    for library in libraries:
        manifest_file = library / f"appmanifest_{steam_id}.acf"
        if manifest_file.exists():
            install_dir = _parse_install_dir_from_manifest(manifest_file)
            if install_dir:
                full_path = library / "common" / install_dir
                if full_path.exists():
                    logger.info(f"Found Steam game {steam_id} at {full_path}")
                    return full_path

    return None


def _parse_install_dir_from_manifest(manifest_path: Path) -> Optional[str]:
    """Parse the installdir from a Steam appmanifest .acf file."""
    try:
        content = manifest_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'"installdir"\s+"([^"]+)"', content)
        if match:
            return match.group(1)
    except Exception as e:
        logger.error(f"Error parsing {manifest_path}: {e}")
    return None


def probe_save_paths(paths: list[str], install_dir: Optional[Path] = None) -> list[Path]:
    """
    Check which save paths actually exist on the filesystem.

    Resolves placeholders and returns only paths that exist.
    """
    from .registry import _PLACEHOLDERS

    found = []
    for template in paths:
        path_str = template

        if "{install_dir}" in path_str:
            if install_dir is None:
                continue
            path_str = path_str.replace("{install_dir}", str(install_dir))

        for placeholder, value in _PLACEHOLDERS.items():
            if placeholder in path_str:
                path_str = path_str.replace(placeholder, str(value))

        path = Path(path_str)
        if path.exists():
            found.append(path)

    return found


def get_running_processes() -> set[str]:
    """
    Get the set of currently running process names (lowercase).

    Uses the Windows API via ctypes to avoid a psutil dependency.
    """
    processes = set()

    try:
        # Use Windows Toolhelp32 API
        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", ctypes.c_ulong),
                ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_char * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1:
            return processes

        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if kernel32.Process32First(snapshot, ctypes.byref(pe)):
            while True:
                name = pe.szExeFile.decode("utf-8", errors="replace").lower()
                processes.add(name)
                if not kernel32.Process32Next(snapshot, ctypes.byref(pe)):
                    break

        kernel32.CloseHandle(snapshot)
    except Exception as e:
        logger.error(f"Error enumerating processes: {e}")

    return processes


def is_game_running(process_name: str) -> bool:
    """Check if a specific game process is currently running."""
    return process_name.lower() in get_running_processes()
