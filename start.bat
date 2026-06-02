@echo off
title ZOMBIELAND C2 LAB - STARTUP PANEL
color 0B
cls

echo =======================================================================
echo          ______  ____  ___ ___  ____   ____   ___   _____
echo         ^|      ^|/    ^|/   ^|   ^|/    ^| ^|    ^| /   \ ^|     ^|
echo         ^|      ^|  o  ^|  _   _  ^|  o  ^|  ^|  ^| ^|     ^|^|  _  ^|
echo         ^|_^|  ^|_^|  _  ^|  ^|_^|  ^|  ^|  _  ^|  ^|  ^| ^|  O  ^|^|  ^|  ^|
echo           ^|  ^| ^|  ^|  ^|  ^| ^|  ^|  ^|  ^|  ^|  ^|  ^| ^|     ^|^|  ^|  ^|
echo           ^|  ^| ^|  ^|  ^|  ^| ^|  ^|  ^|  ^|  ^|  ^|  ^| ^|     ^|^|  ^|  ^|
echo           ^|__^| ^|__^|__^|__^| ^|__^|__^|__^|__^| [__^|__^| \___/ ^|__^|__^|
echo.
echo                 CYBERSECURITY ETHICAL TRAINING LAB
echo =======================================================================
echo.

:: 1. Check Python installation
echo [+] Checking Python installation...
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Python not found in system PATH. Checking Miniconda/Anaconda...
    if exist "%USERPROFILE%\miniconda3\python.exe" (
        set PYTHON_CMD="%USERPROFILE%\miniconda3\python.exe"
        echo [INFO] Found Miniconda at %USERPROFILE%\miniconda3
    ) else if exist "%USERPROFILE%\AppData\Local\miniconda3\python.exe" (
        set PYTHON_CMD="%USERPROFILE%\AppData\Local\miniconda3\python.exe"
        echo [INFO] Found Miniconda at AppData\Local\miniconda3
    ) else if exist "C:\ProgramData\miniconda3\python.exe" (
        set PYTHON_CMD="C:\ProgramData\miniconda3\python.exe"
        echo [INFO] Found Miniconda at C:\ProgramData\miniconda3
    ) else if exist "%USERPROFILE%\Anaconda3\python.exe" (
        set PYTHON_CMD="%USERPROFILE%\Anaconda3\python.exe"
        echo [INFO] Found Anaconda at %USERPROFILE%\Anaconda3
    ) else (
        echo [ERROR] Python, Miniconda, or Anaconda is not installed or not configured.
        echo Please install Python 3.8+ or Miniconda and add it to your environment.
        echo Press any key to exit.
        pause >nul
        exit /b
    )
)

:: 2. Install dependencies
echo [+] Checking and installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [-] Pip install failed. Attempting user-level install...
    %PYTHON_CMD% -m pip install -r requirements.txt --user --quiet
)

:: 3. Launch portal in browser
echo [+] Launching Zombieland Web Portal in default browser...
start http://localhost:5000

:: 4. Start C2 and Web Server
echo [+] Launching C2 Socket listener and Flask Server...
echo [INFO] C2 Engine listening on TCP port 5555
echo [INFO] Flask Web Server running on HTTP port 5000
echo.
echo Press Ctrl+C in this terminal to stop the servers.
echo =======================================================================
echo.
%PYTHON_CMD% server.py

pause
