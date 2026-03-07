@echo off
cd /d "T:\Github\sb4ssman\SKsSuperSlickandStealthySaveSaver"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)
"T:\Github\sb4ssman\SKsSuperSlickandStealthySaveSaver\.venv\Scripts\pythonw.exe" "T:\Github\sb4ssman\SKsSuperSlickandStealthySaveSaver\App\SuperSaveSaver.py" %*
exit /b
