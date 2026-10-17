@echo off
cd /d "%~dp0"
python review_candidates_keyboard.py --mode fp --csv review_junior.csv --sorted-dir review_sorted_junior
if errorlevel 1 pause
