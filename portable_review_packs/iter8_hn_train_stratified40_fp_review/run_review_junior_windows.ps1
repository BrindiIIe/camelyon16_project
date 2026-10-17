$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
python .\review_candidates_keyboard.py --mode fp --csv .\review_junior.csv --sorted-dir .\review_sorted_junior
