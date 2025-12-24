@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PROFILE_DIR=%SCRIPT_DIR%Headless Test\chrome_profile"

if defined HEYGEN_PYTHON (
  set "PYTHON_CMD=%HEYGEN_PYTHON%"
) else (
  set "PYTHON_CMD="
  py -3 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3"
  if not defined PYTHON_CMD (
    python -c "import sys" >nul 2>&1 && set "PYTHON_CMD=python"
  )
  if not defined PYTHON_CMD (
    python3 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=python3"
  )
)

if not defined PYTHON_CMD (
  echo Python not found. Install Python 3 or set HEYGEN_PYTHON.
  pause
  exit /b 1
)

if not exist "%PROFILE_DIR%" (
  echo Chrome profile not found. Launching first-time login...
  call %PYTHON_CMD% "Headless Test\setup_profile.py"
  if errorlevel 1 (
    echo Setup failed.
    pause
    exit /b 1
  )
)

call %PYTHON_CMD% "Headless Test\ui_server.py"
pause
