@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0..\..\myenv_win\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo Environnement Python du projet introuvable: %PROJECT_PYTHON%
  pause
  exit /b 1
)
"%PROJECT_PYTHON%" review_candidates_keyboard.py --mode fp --csv review_ph.csv --sorted-dir review_sorted_ph
if errorlevel 1 pause
