from pathlib import Path
import argparse
import csv
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
    dst = unique_path(dst_dir / f"{safe_slide}_c{safe_component}_{src.name}")
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
    readme = f"""# Portable False-Positive Review Pack

This folder is self-contained for visual review.

## Independent-review protocol

For the next review batch, the junior resident and the senior pathologist
(`PH`) must classify the candidates independently before comparing answers.
Use separate copies of `review_template.csv`; do not show either reviewer the
other person's answers until both files are complete.

After both reviews are frozen, compare the binary label, morphology category,
difficulty type, and hard-negative inclusion decision. Preserve the two
initial answers and record the post-discussion consensus in a third file. The
analysis should report the percentage of exact agreement and, when suitable,
Cohen's kappa. Do not replace an initial answer with the consensus answer.

## Windows

From PowerShell:

```powershell
./run_review_windows.ps1
```

If Python packages are missing:

```powershell
python -m pip install matplotlib pillow
```

## macOS

From Terminal:

```bash
chmod +x run_review_mac.sh
./run_review_mac.sh
```

If Python packages are missing:

```bash
python3 -m pip install matplotlib pillow
```

The review updates the selected CSV in place and copies reviewed images into
`review_sorted/`. Before starting an independent review, duplicate
`review_template.csv` and give the copy a reviewer-specific name.
"""
    (pack_dir / "run_review_windows.ps1").write_text(windows, encoding="utf-8")
    mac_path = pack_dir / "run_review_mac.sh"
    mac_path.write_text(mac, encoding="utf-8")
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
