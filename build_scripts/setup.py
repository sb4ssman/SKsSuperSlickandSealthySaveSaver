"""
Setup script for SK's Super Slick and Stealthy Save Saver.

Handles:
    - Creating a .venv virtual environment
    - Installing Python dependencies into it
    - Asking the user if they want it to run on Windows startup
    - Creating/removing a .bat file in the Windows startup folder

Usage:
    python build_scripts/setup.py       (or via setup.bat)
"""

import os
import subprocess
import sys
import venv
from pathlib import Path

APP_DIR = Path(__file__).parent.parent.resolve()
VENV_DIR = APP_DIR / ".venv"
APP_NAME = "SKsSuperSaveSaver"
STARTUP_BAT_NAME = f"{APP_NAME}.bat"


def get_venv_python() -> Path:
    """Get the python executable inside the venv."""
    return VENV_DIR / "Scripts" / "python.exe"


def get_venv_pythonw() -> Path:
    """Get the pythonw executable inside the venv (no console window)."""
    return VENV_DIR / "Scripts" / "pythonw.exe"


def create_venv() -> bool:
    """Create a virtual environment if it doesn't exist."""
    if VENV_DIR.exists() and get_venv_python().exists():
        print(f"Virtual environment already exists: {VENV_DIR}")
        return True

    print(f"Creating virtual environment: {VENV_DIR}")
    try:
        venv.create(str(VENV_DIR), with_pip=True)
        print("Virtual environment created successfully.")
        return True
    except Exception as e:
        print(f"Failed to create virtual environment: {e}")
        return False


def install_dependencies() -> bool:
    """Install required Python packages into the venv."""
    requirements = APP_DIR / "requirements.txt"
    if not requirements.exists():
        print("requirements.txt not found — skipping dependency install.")
        return True

    python = get_venv_python()
    if not python.exists():
        print(f"Venv python not found at {python} — run setup again.")
        return False

    print("Installing dependencies into .venv...")
    result = subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(requirements)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("Dependencies installed successfully.")
        return True
    else:
        print(f"Failed to install dependencies:\n{result.stderr}")
        return False


def get_startup_folder() -> Path:
    """Get the Windows startup folder path."""
    return Path(os.environ["APPDATA"]) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_startup_bat_path() -> Path:
    return get_startup_folder() / STARTUP_BAT_NAME


def add_to_startup() -> bool:
    """Create a .bat file in the Windows startup folder."""
    startup_folder = get_startup_folder()
    if not startup_folder.exists():
        print(f"Startup folder not found: {startup_folder}")
        return False

    # Use pythonw from the venv so it runs without a console window
    pythonw = get_venv_pythonw()
    if not pythonw.exists():
        # Fallback to venv python.exe
        pythonw = get_venv_python()
        print(f"Warning: pythonw.exe not found in venv, using {pythonw}")

    script_path = APP_DIR / "SuperSaveSaver.py"

    bat_content = (
        f'@echo off\n'
        f'cd /d "{APP_DIR}"\n'
        f'start /B "" "{pythonw}" "{script_path}" --silent\n'
        f'exit /b\n'
    )

    bat_path = get_startup_bat_path()
    try:
        bat_path.write_text(bat_content)
        print(f"Added to startup: {bat_path}")
        return True
    except Exception as e:
        print(f"Failed to create startup script: {e}")
        return False


def remove_from_startup() -> bool:
    """Remove the startup .bat file."""
    bat_path = get_startup_bat_path()
    if bat_path.exists():
        bat_path.unlink()
        print(f"Removed from startup: {bat_path}")
        return True
    else:
        print("Not currently in startup.")
        return True


def is_in_startup() -> bool:
    return get_startup_bat_path().exists()


def main():
    print()
    print("=" * 50)
    print("  SK's Super Slick and Stealthy Save Saver")
    print("  Setup")
    print("=" * 50)
    print()

    # Step 1: Create venv
    if not create_venv():
        print("Setup failed — could not create virtual environment.")
        return
    print()

    # Step 2: Install dependencies
    if not install_dependencies():
        print("Setup failed — could not install dependencies.")
        return
    print()

    # Step 3: Ask about startup
    currently_installed = is_in_startup()
    if currently_installed:
        print("SSSSSS is currently set to run on startup.")
        choice = input("Remove from startup? [y/N]: ").strip().lower()
        if choice == "y":
            remove_from_startup()
    else:
        choice = input("Would you like SSSSSS to run silently on startup? [Y/n]: ").strip().lower()
        if choice != "n":
            add_to_startup()
        else:
            print("Skipped. You can run setup.py again later to add it.")

    print()
    print("Setup complete.")
    print(f"To run manually:  .venv\\Scripts\\python SuperSaveSaver.py")
    print()


if __name__ == "__main__":
    main()