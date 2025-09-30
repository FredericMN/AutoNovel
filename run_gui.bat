@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

title AI_NovelGenerator - Run GUI

rem Unbuffered, UTF-8 output from Python so logs are visible
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

set "VENV_PY=%ROOT%venv\Scripts\python.exe"

if exist "venv\Scripts\activate.bat" (
  echo [INFO] Using existing virtual environment.
) else (
  echo [INFO] Creating virtual environment...
  where py >nul 2>&1
  if %errorlevel%==0 (
    py -m venv venv
  ) else (
    python -m venv venv
  )
  if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
  echo [INFO] Installing requirements...
  call "venv\Scripts\activate.bat"
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r requirements.txt
)

call "venv\Scripts\activate.bat"

if not exist "%VENV_PY%" (
  echo [ERROR] Missing virtual environment interpreter: %VENV_PY%
  pause
  exit /b 1
)

"%VENV_PY%" -m pip show customtkinter >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing requirements...
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r requirements.txt
)

:RUN
echo [INFO] Using interpreter: %VENV_PY%
"%VENV_PY%" -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] customtkinter import check failed. Please verify the virtual environment.
  pause
  exit /b 1
)
echo [INFO] Starting application...
"%VENV_PY%" main.py

echo.
echo [INFO] Application exited with code %errorlevel%
echo Press any key to close...
pause >nul
endlocal
exit /b
