#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export AUTONOVEL_LLM_STDOUT=1
export AUTONOVEL_LLM_LOG_PAYLOAD=1

VENV_PY="$ROOT/venv/bin/python"

if [[ -x "$VENV_PY" ]]; then
  if "$VENV_PY" - <<'PY' >/dev/null 2>&1
import sys
import tkinter
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
  then
    echo "[INFO] Using existing virtual environment."
  else
    echo "[WARN] Existing venv missing tkinter or uses Python < 3.10; recreating..."
    rm -rf "$ROOT/venv"
  fi
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "[INFO] Creating virtual environment..."
  PYTHON_CMD=""
  PYTHON_FALLBACK=0
  # Prefer Homebrew Python with Tk support when available.
  if [[ -x /opt/homebrew/bin/python3.12 ]]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.12"
  elif command -v pyenv >/dev/null 2>&1; then
    PYENV_ROOT="$(pyenv root)"
    export PATH="$PYENV_ROOT/shims:$PATH"
  fi

  if [[ -z "$PYTHON_CMD" ]]; then
    if command -v python3.12 >/dev/null 2>&1; then
      PYTHON_CMD="python3.12"
    elif command -v python3.11 >/dev/null 2>&1; then
      PYTHON_CMD="python3.11"
    elif command -v python3.10 >/dev/null 2>&1; then
      PYTHON_CMD="python3.10"
    elif command -v python3 >/dev/null 2>&1; then
      PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
      PYTHON_CMD="python"
      PYTHON_FALLBACK=1
    fi
  fi

  if [[ -z "$PYTHON_CMD" ]]; then
    echo "[ERROR] Python 3.10+ not found. Please install Python 3.10+ and ensure python3 is available."
    exit 1
  fi

  if ! "$PYTHON_CMD" - <<'PY'
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
  then
    if [[ "$PYTHON_FALLBACK" -eq 1 ]]; then
      echo "[ERROR] python3 not found and 'python' is not 3.10+. Current version: $($PYTHON_CMD -V 2>&1)"
      echo "[ERROR] Please install Python 3.10+ and ensure python3 is available."
    else
      echo "[ERROR] Python 3.10+ is required. Current version: $($PYTHON_CMD -V 2>&1)"
    fi
    exit 1
  fi

  "$PYTHON_CMD" -m venv venv

  if [[ ! -x "$VENV_PY" ]]; then
    echo "[ERROR] Failed to create virtual environment."
    exit 1
  fi

  echo "[INFO] Installing requirements..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt
fi

if ! "$VENV_PY" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  echo "[ERROR] tkinter is not available in this Python build."
  echo "[ERROR] macOS: install Python from python.org or ensure Tk support is included."
  exit 1
fi

if ! "$VENV_PY" -m pip show customtkinter >/dev/null 2>&1; then
  echo "[INFO] Installing requirements..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt
fi

echo "[INFO] Using interpreter: $VENV_PY"
if ! "$VENV_PY" -c "import customtkinter" >/dev/null 2>&1; then
  echo "[ERROR] customtkinter import check failed. Please verify the virtual environment."
  exit 1
fi

echo "[INFO] Starting application..."
"$VENV_PY" main.py
