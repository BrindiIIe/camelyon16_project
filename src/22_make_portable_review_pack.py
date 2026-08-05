from pathlib import Path
import argparse
import csv
import filecmp
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCRIPT = PROJECT_ROOT / "src/17_review_candidates_keyboard.py"

IMAGE_COLUMNS = [
    "contact_sheet",
    "overview",
    "patch_path",
    "reviewed_image",
]


def read_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_rows(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_rows_if_missing(path, rows, fieldnames):
    if path.exists():
        return False
    write_rows(path, rows, fieldnames)
    return True


def resolve_source_path(value, csv_path):
    if not value:
        return None

    path = Path(value)
    candidates = [path]
    if not path.is_absolute():
        candidates.append(csv_path.parent / path)
        candidates.append(PROJECT_ROOT / path)

    for candidate in candidates:
        if candidate.exists() and not candidate.name.startswith("._"):
            return candidate
    return None


def unique_path(path):
    if not path.exists():
        return path
    for idx in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{idx}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {path}")


def copy_image(src, pack_dir, slide_id, component_id):
    kind = "overviews" if "overview" in src.stem.lower() else "images"
    safe_slide = slide_id or "unknown_slide"
    safe_component = component_id or "row"
    dst_dir = pack_dir / kind / safe_slide
    dst_dir.mkdir(parents=True, exist_ok=True)
    expected = dst_dir / f"{safe_slide}_c{safe_component}_{src.name}"
    if expected.exists() and filecmp.cmp(src, expected, shallow=False):
        return expected.relative_to(pack_dir)
    dst = unique_path(expected)
    shutil.copy2(src, dst)
    return dst.relative_to(pack_dir)


def write_launcher_files(pack_dir, mode):
    windows = f"""$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
python .\\review_candidates_keyboard.py --mode {mode} --csv .\\review_template.csv --sorted-dir .\\review_sorted
"""
    mac = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python ./review_candidates_keyboard.py --mode {mode} --csv ./review_template.csv --sorted-dir ./review_sorted --fig-width 16 --fig-height 12
"""
    windows_junior = windows.replace(
        ".\\review_template.csv --sorted-dir .\\review_sorted",
        ".\\review_junior.csv --sorted-dir .\\review_sorted_junior",
    )
    windows_ph = windows.replace(
        ".\\review_template.csv --sorted-dir .\\review_sorted",
        ".\\review_ph.csv --sorted-dir .\\review_sorted_ph",
    )
    cmd_junior = fr"""@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0..\..\myenv_win\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo Environnement Python du projet introuvable: %PROJECT_PYTHON%
  echo Replacez ce dossier dans camelyon16_project\portable_review_packs.
  pause
  exit /b 1
)
"%PROJECT_PYTHON%" review_candidates_keyboard.py --mode {mode} --csv review_junior.csv --sorted-dir review_sorted_junior
if errorlevel 1 pause
"""
    cmd_ph = fr"""@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0..\..\myenv_win\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo Environnement Python du projet introuvable: %PROJECT_PYTHON%
  echo Replacez ce dossier dans camelyon16_project\portable_review_packs.
  pause
  exit /b 1
)
"%PROJECT_PYTHON%" review_candidates_keyboard.py --mode {mode} --csv review_ph.csv --sorted-dir review_sorted_ph
if errorlevel 1 pause
"""
    cmd_junior_context = cmd_junior.replace(
        "--sorted-dir review_sorted_junior",
        "--sorted-dir review_sorted_junior --include-reviewed --fig-width 18 --fig-height 10",
    )
    cmd_consensus = fr"""@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0..\..\myenv_win\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo Environnement Python du projet introuvable: %PROJECT_PYTHON%
  echo Replacez ce dossier dans camelyon16_project\portable_review_packs.
  pause
  exit /b 1
)
"%PROJECT_PYTHON%" review_candidates_keyboard.py --mode {mode} --csv review_consensus.csv --reference-csv review_junior.csv --sorted-dir review_sorted_consensus --include-reviewed --fig-width 18 --fig-height 10
if errorlevel 1 pause
"""
    mac_junior = mac.replace(
        "./review_template.csv --sorted-dir ./review_sorted",
        "./review_junior.csv --sorted-dir ./review_sorted_junior",
    )
    mac_ph = mac.replace(
        "./review_template.csv --sorted-dir ./review_sorted",
        "./review_ph.csv --sorted-dir ./review_sorted_ph",
    )
    mac_consensus = mac.replace(
        "./review_template.csv --sorted-dir ./review_sorted",
        "./review_consensus.csv --reference-csv ./review_junior.csv --sorted-dir ./review_sorted_consensus --include-reviewed",
    )
    readme = f"""# Portable False-Positive Review Pack

This folder is self-contained for visual review.

## Independent-review protocol

For the next review batch, the junior resident and the senior pathologist
(`PH`) must classify the candidates independently before comparing answers.
Use `review_junior.csv` and `review_ph.csv` independently; do not show either
reviewer the other person's answers until both files are complete.

After both reviews are frozen, compare the binary label, morphology category,
difficulty type, and hard-negative inclusion decision. Preserve the two
initial answers and record the post-discussion consensus in a third file. The
analysis should report the percentage of exact agreement and, when suitable,
Cohen's kappa. Do not replace an initial answer with the consensus answer.

For the later joint review, the consensus launcher displays the junior's
already-frozen answer in the window title. It reads `review_junior.csv`
without modifying it and writes the joint decision only to
`review_consensus.csv`.

## Windows

The recommended launchers do not require changing the PowerShell execution
policy. From PowerShell or Command Prompt:

```powershell
./run_review_junior_windows.cmd
# or, on the PH's independent copy:
./run_review_ph_windows.cmd
# or, for the joint review with junior answers visible:
./run_review_consensus_with_junior_windows.cmd
```

If Python packages are missing:

```powershell
python -m pip install matplotlib pillow
```

## macOS

From Terminal:

```bash
chmod +x run_review_mac.sh
chmod +x run_review_junior_mac.sh run_review_ph_mac.sh
./run_review_junior_mac.sh
# or, on the PH's independent copy:
./run_review_ph_mac.sh
# or, for the joint review with junior answers visible:
./run_review_consensus_with_junior_mac.sh
```

If Python packages are missing:

```bash
python3 -m pip install matplotlib pillow
```

The review updates the selected reviewer CSV in place and copies reviewed
images into its reviewer-specific `review_sorted_*` folder. Keep
`review_consensus.csv` blank until both independent reviews have been frozen
and the disagreement discussion begins. `review_template.csv` is an untouched
master copy.
"""
    (pack_dir / "run_review_windows.ps1").write_text(windows, encoding="utf-8")
    (pack_dir / "run_review_junior_windows.ps1").write_text(
        windows_junior, encoding="utf-8"
    )
    (pack_dir / "run_review_ph_windows.ps1").write_text(windows_ph, encoding="utf-8")
    (pack_dir / "run_review_junior_windows.cmd").write_text(
        cmd_junior, encoding="utf-8"
    )
    (pack_dir / "run_review_ph_windows.cmd").write_text(cmd_ph, encoding="utf-8")
    (pack_dir / "run_review_junior_context_windows.cmd").write_text(
        cmd_junior_context, encoding="utf-8"
    )
    (pack_dir / "run_review_consensus_with_junior_windows.cmd").write_text(
        cmd_consensus, encoding="utf-8"
    )
    mac_path = pack_dir / "run_review_mac.sh"
    mac_path.write_text(mac, encoding="utf-8")
    (pack_dir / "run_review_junior_mac.sh").write_text(mac_junior, encoding="utf-8")
    (pack_dir / "run_review_ph_mac.sh").write_text(mac_ph, encoding="utf-8")
    (pack_dir / "run_review_consensus_with_junior_mac.sh").write_text(
        mac_consensus, encoding="utf-8"
    )
    (pack_dir / "README_REVIEW.md").write_text(readme, encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a portable image+CSV pack for keyboard review."
    )
    parser.add_argument("--csv", required=True, help="Source review_template.csv")
    parser.add_argument("--output-dir", required=True, help="Portable pack directory")
    parser.add_argument("--mode", choices=["fp", "hp"], default="fp")
    parser.add_argument(
        "--include-reviewed",
        action="store_true",
        help="Keep already reviewed rows. By default all rows are copied too; this flag is kept for explicitness.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    pack_dir = Path(args.output_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)

    rows, fieldnames = read_rows(csv_path)
    if fieldnames is None:
        raise ValueError(f"CSV has no header: {csv_path}")

    copied = {}
    missing = []
    rewritten_rows = []

    for row in rows:
        new_row = dict(row)
        slide_id = row.get("slide_id", "")
        component_id = row.get("component_id", "") or row.get("candidate_id", "")

        for column in IMAGE_COLUMNS:
            value = row.get(column)
            if not value:
                continue

            src = resolve_source_path(value, csv_path)
            if src is None:
                missing.append((row.get("slide_id", ""), column, value))
                continue

            key = str(src.resolve())
            if key not in copied:
                copied[key] = copy_image(src, pack_dir, slide_id, component_id)
            new_row[column] = copied[key].as_posix()

        rewritten_rows.append(new_row)

    write_rows(pack_dir / "review_template.csv", rewritten_rows, fieldnames)
    write_rows_if_missing(pack_dir / "review_junior.csv", rewritten_rows, fieldnames)
    write_rows_if_missing(pack_dir / "review_ph.csv", rewritten_rows, fieldnames)
    write_rows_if_missing(
        pack_dir / "review_consensus.csv", rewritten_rows, fieldnames
    )
    shutil.copy2(REVIEW_SCRIPT, pack_dir / "review_candidates_keyboard.py")
    write_launcher_files(pack_dir, args.mode)

    print("Portable review pack:", pack_dir)
    print("Rows:", len(rewritten_rows))
    print("Images copied:", len(copied))
    print("Missing image references:", len(missing))
    if missing:
        print("First missing references:")
        for slide_id, column, value in missing[:10]:
            print(f"  {slide_id} {column}: {value}")


if __name__ == "__main__":
    main()
