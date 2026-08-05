@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0..\..\myenv_win\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo Environnement Python du projet introuvable: %PROJECT_PYTHON%
  echo Replacez ce dossier dans camelyon16_project\portable_review_packs.
  pause
  exit /b 1
)
"%PROJECT_PYTHON%" review_candidates_keyboard.py --mode fp --csv review_consensus.csv --reference-csv review_junior.csv --sorted-dir review_sorted_consensus --include-reviewed --fig-width 18 --fig-height 10
if errorlevel 1 pause
