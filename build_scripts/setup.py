"""
Setup script for SK's Super Slick and Stealthy Save Saver.

Handles:
    - Creating a .venv virtual environment
    - Installing Python dependencies into it
    - Creating SaveAllTheGames.bat launcher
    - Asking the user if they want it to run on Windows startup
    - Creating/removing a .bat file in the Windows startup folder

Usage:
    python build_scripts/setup.py [--startup|--no-startup|--remove-startup]
    
    Options:
        --startup          Add to Windows startup (non-interactive)
        --no-startup       Skip startup installation (non-interactive)
        --remove-startup   Remove from Windows startup (non-interactive)
        
    If no option is provided, will prompt interactively (if possible).
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
LAUNCHER_BAT_NAME = "SaveAllTheGames.bat"

# Track actions taken during setup
setup_actions = []


def get_venv_python() -> Path:
    """Get the python executable inside the venv."""
    return VENV_DIR / "Scripts" / "python.exe"


def get_venv_pythonw() -> Path:
    """Get the pythonw executable inside the venv (no console window)."""
    return VENV_DIR / "Scripts" / "pythonw.exe"


def check_python_version() -> bool:
    """Check if Python version is 3.6 or later."""
    if sys.version_info < (3, 6):
        print(f"Error: Python 3.6 or later is required. Found: {sys.version}")
        return False
    print(f"Python version check: {sys.version.split()[0]} (OK)")
    return True


def create_venv() -> bool:
    """Create a virtual environment if it doesn't exist."""
    if VENV_DIR.exists() and get_venv_python().exists():
        print(f"Virtual environment already exists: {VENV_DIR}")
        setup_actions.append("✓ Virtual environment verified")
        return True

    print(f"Creating virtual environment: {VENV_DIR}")
    try:
        venv.create(str(VENV_DIR), with_pip=True)
        print("Virtual environment created successfully.")
        setup_actions.append("✓ Created virtual environment")
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
        setup_actions.append("✓ Installed Python dependencies")
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


def get_launcher_bat_path() -> Path:
    """Get the path to the SaveAllTheGames.bat launcher in the app directory."""
    return APP_DIR / LAUNCHER_BAT_NAME


def create_launcher_bat() -> bool:
    """Create SaveAllTheGames.bat launcher file in the app directory."""
    pythonw = get_venv_pythonw()
    if not pythonw.exists():
        # Fallback to venv python.exe
        pythonw = get_venv_python()
        print(f"Warning: pythonw.exe not found in venv, using {pythonw}")

    script_path = APP_DIR / "App" / "SuperSaveSaver.py"

    bat_content = (
        f'@echo off\n'
        f'cd /d "{APP_DIR}"\n'
        f'if not exist ".venv\\Scripts\\pythonw.exe" (\n'
        f'    echo Virtual environment not found. Please run setup.bat first.\n'
        f'    pause\n'
        f'    exit /b 1\n'
        f')\n'
        f'"{pythonw}" "{script_path}" %*\n'
        f'exit /b\n'
    )

    launcher_path = get_launcher_bat_path()
    try:
        launcher_path.write_text(bat_content)
        print(f"Created launcher: {launcher_path}")
        setup_actions.append(f"✓ Created {LAUNCHER_BAT_NAME}")
        return True
    except Exception as e:
        print(f"Failed to create launcher script: {e}")
        return False


def add_to_startup() -> bool:
    """Create a .bat file in the Windows startup folder that calls SaveAllTheGames.bat."""
    startup_folder = get_startup_folder()
    if not startup_folder.exists():
        print(f"Startup folder not found: {startup_folder}")
        return False

    launcher_path = get_launcher_bat_path()
    if not launcher_path.exists():
        print(f"Launcher not found: {launcher_path}")
        print("Creating launcher first...")
        if not create_launcher_bat():
            return False

    # Create startup bat that calls the launcher with --silent flag
    bat_content = (
        f'@echo off\n'
        f'cd /d "{APP_DIR}"\n'
        f'start /B "" "{launcher_path}" --silent\n'
        f'exit /b\n'
    )

    bat_path = get_startup_bat_path()
    try:
        bat_path.write_text(bat_content)
        print(f"Added to startup: {bat_path}")
        setup_actions.append("✓ Added to Windows startup")
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
        setup_actions.append("✓ Removed from Windows startup")
        return True
    else:
        print("Not currently in startup.")
        return True


def is_in_startup() -> bool:
    return get_startup_bat_path().exists()


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input, with fallback to default for non-interactive terminals."""
    if not sys.stdin.isatty():
        # Non-interactive - return default
        print(f"{prompt}{default}")
        return default
    
    try:
        user_input = input(prompt).strip()
        return user_input if user_input else default
    except (EOFError, KeyboardInterrupt):
        return default


def main():
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Setup script for SK's Super Slick and Stealthy Save Saver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--startup", action="store_true",
        help="Add to Windows startup (non-interactive)",
    )
    parser.add_argument(
        "--no-startup", action="store_true",
        help="Skip startup installation (non-interactive)",
    )
    parser.add_argument(
        "--remove-startup", action="store_true",
        help="Remove from Windows startup (non-interactive)",
    )
    args = parser.parse_args()
    
    # Determine startup action from args
    startup_action = None  # None = interactive, "add" = add, "skip" = skip, "remove" = remove
    if args.startup:
        startup_action = "add"
    elif args.no_startup:
        startup_action = "skip"
    elif args.remove_startup:
        startup_action = "remove"
    
    print()
    print("=" * 50)
    print("  SK's Super Slick and Stealthy Save Saver")
    print("  Setup")
    print("=" * 50)
    print()

    # Step 0: Check Python version
    if not check_python_version():
        print("Setup failed — Python version too old.")
        sys.exit(1)
    print()

    # Step 1: Create venv
    if not create_venv():
        print("Setup failed — could not create virtual environment.")
        sys.exit(1)
    print()

    # Step 2: Install dependencies
    if not install_dependencies():
        print("Setup failed — could not install dependencies.")
        sys.exit(1)
    print()

    # Step 3: Create launcher bat
    if not create_launcher_bat():
        print("Warning: Could not create launcher bat file.")
    print()

    # Step 4: Handle startup
    currently_installed = is_in_startup()
    
    if startup_action == "remove":
        # Explicit remove command
        if currently_installed:
            remove_from_startup()
        else:
            print("Not currently in startup.")
            setup_actions.append("○ Not in startup (nothing to remove)")
    elif startup_action == "add":
        # Explicit add command
        if currently_installed:
            print("Already in startup.")
            setup_actions.append("○ Already in Windows startup")
        else:
            add_to_startup()
    elif startup_action == "skip":
        # Explicit skip command
        print("Skipping startup installation (--no-startup specified).")
        setup_actions.append("○ Skipped startup installation")
        # Remove old entry if it exists
        if currently_installed:
            print("Removing old startup entry...")
            remove_from_startup()
    else:
        # Interactive mode
        if currently_installed:
            print("SSSSSS is currently set to run on startup.")
            choice = get_user_input("Remove from startup? [y/N]: ", "N").lower()
            if choice == "y":
                remove_from_startup()
            else:
                setup_actions.append("○ Kept in Windows startup")
        else:
            choice = get_user_input("Would you like SSSSSS to run silently on startup? [Y/n]: ", "Y").lower()
            if choice != "n":
                add_to_startup()
            else:
                print("Skipped startup installation.")
                setup_actions.append("○ Skipped startup installation")
                # If user declined, check if there's an old entry and remove it
                if is_in_startup():
                    print("Removing old startup entry...")
                    remove_from_startup()

    # Print summary
    print()
    print("=" * 50)
    print("  Setup Complete")
    print("=" * 50)
    print()
    if setup_actions:
        print("Actions taken:")
        for action in setup_actions:
            print(f"  {action}")
        print()
    print("To run manually:")
    print(f"  {LAUNCHER_BAT_NAME}")
    print(f"  or: .venv\\Scripts\\python App\\SuperSaveSaver.py")
    print()


if __name__ == "__main__":
    main()