@echo off
cd /d "%~dp0"
python review_candidates_keyboard.py --mode fp --csv review_ph.csv --sorted-dir review_sorted_ph
if errorlevel 1 pause
