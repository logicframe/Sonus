@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo YouTube Music Desktop
echo Selecting Python interpreter...
echo ========================================

set "PYTHON_CMD="
set "PYTHONW_EXE="

REM Prefer Python 3.13 because pygame 2.6.1 provides a Windows wheel for CPython 3.13.
py -3.13 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,13) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.13"
) else (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,13) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    ) else (
        echo.
        echo ERROR: Python 3.13 was not found.
        echo.
        echo This project currently requires Python 3.13 because
        echo pygame 2.6.1 does not provide a Windows wheel for Python 3.14.
        echo Install Python 3.13, then run this file again.
        echo.
        pause
        exit /b 1
    )
)

if "%PYTHON_CMD%"=="py -3.13" (
    for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%P"
) else (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%P"
)

set "PYTHON_DIR=%PYTHON_EXE:\python.exe=%"
set "PYTHONW_EXE=%PYTHON_DIR%\pythonw.exe"

if not exist "%PYTHONW_EXE%" (
    echo.
    echo ERROR: pythonw.exe was not found next to the selected Python interpreter.
    echo Expected: "%PYTHONW_EXE%"
    echo.
    pause
    exit /b 1
)

echo Using: %PYTHON_EXE%
echo.
%PYTHON_CMD% --version

echo.
echo ========================================
echo Checking Python dependencies...
echo ========================================

%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install/check Python dependencies.
    echo.
    pause
    exit /b 2
)

echo.
echo Verifying pygame...
%PYTHON_CMD% -c "import pygame; print('pygame', pygame.version.ver, 'OK')"
if errorlevel 1 (
    echo.
    echo ERROR: pygame could not be imported by the selected Python.
    echo.
    pause
    exit /b 3
)

echo.
echo Checking FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: FFmpeg was not found in PATH.
    echo Install FFmpeg and make sure ffmpeg.exe is available from a new terminal.
    echo.
    pause
    exit /b 4
)

echo.
echo ========================================
echo Starting application...
echo ========================================
echo.

REM Launch pythonw.exe as a detached Windows process. Do NOT use START /B with the
REM Python launcher: that keeps the child associated with the console lifetime.
start "YouTube Music Desktop" "%PYTHONW_EXE%" "%~dp0app.py"
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start the GUI application.
    echo.
    pause
    exit /b 5
)

exit /b 0
