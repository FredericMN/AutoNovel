@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

title AI_NovelGenerator - Run GUI

rem Unbuffered, UTF-8 output from Python so logs are visible
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

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
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  goto RUN
)

call "venv\Scripts\activate.bat"
:RUN
echo [INFO] Starting application...
python main.py

echo.
echo [INFO] Application exited with code %errorlevel%
echo Press any key to close...
pause >nul
endlocal
exit /b
