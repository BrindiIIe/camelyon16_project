from pathlib import Path
import argparse
import csv
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data/patches_iter2/train"
OUTPUT_DIR = PROJECT_ROOT / "data/patches_iter5/train"
FP_REVIEW_CSV = PROJECT_ROOT / "outputs/iter4_fp_review/review_template.csv"
HP_REVIEW_CSV = PROJECT_ROOT / "outputs/hard_positive_review_iter2/review_template.csv"
SUMMARY_DIR = PROJECT_ROOT / "outputs/iter5_dataset"

LEGACY_PROJECT_ROOTS = [
    Path("/Volumes/TX/camelyon16_project"),
]
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def resolve_path(value):
    path = Path(value)
    candidates = [path]

    for legacy_root in LEGACY_PROJECT_ROOTS:
        try:
            relative = path.relative_to(legacy_root)
        except ValueError:
            continue
        candidates.append(PROJECT_ROOT / relative)

    for candidate in candidates:
        if candidate.exists() and not candidate.name.startswith("._"):
            return candidate
    return None


def is_patch_file(path):
    path = Path(path)
    if path.name.startswith("._"):
        return False
    if path.suffix.lower() not in VALID_EXTENSIONS:
        return False
    return "contact_sheet" not in path.name and "overview" not in path.name


def count_images(folder):
    counts = {}
    for label in ["normal", "tumor"]:
        label_dir = Path(folder) / label
        counts[label] = sum(
            1
            for path in label_dir.iterdir()
            if path.is_file() and is_patch_file(path)
        ) if label_dir.exists() else 0
    counts["total"] = counts["normal"] + counts["tumor"]
    return counts


def read_selected_rows(review_csv, include_column):
    selected = []
    with open(review_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = row.get(include_column, "").strip().lower()
            if decision == "yes":
                selected.append(row)
    return selected


def copy_base_dataset(source_dir, output_dir, overwrite):
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"{output_dir} existe deja. Relancer avec --overwrite pour reconstruire iter5."
            )
        shutil.rmtree(output_dir)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_dir,
        output_dir,
        ignore=shutil.ignore_patterns("._*", "__pycache__"),
    )


def copy_hard_negatives(selected_rows, output_dir):
    added = []
    normal_dir = output_dir / "normal"
    normal_dir.mkdir(parents=True, exist_ok=True)

    for row in selected_rows:
        contact_sheet = resolve_path(row.get("contact_sheet", ""))
        if contact_sheet is None:
            raise FileNotFoundError(f"Contact sheet introuvable: {row.get('contact_sheet', '')}")

        patch_dir = contact_sheet.parent
        source_patches = sorted(
            path for path in patch_dir.iterdir()
            if path.is_file() and is_patch_file(path)
        )

        for source_path in source_patches:
            dest_name = (
                f"iter5_hn_{row['slide_id']}_c{int(row['component_id']):02d}_"
                f"{source_path.name}"
            )
            dest_path = normal_dir / dest_name
            shutil.copy2(source_path, dest_path)
            added.append({
                "type": "hard_negative",
                "slide_id": row["slide_id"],
                "candidate_id": "",
                "component_id": row["component_id"],
                "review_category": row.get("review_category", ""),
                "difficulty_type": row.get("difficulty_type", ""),
                "source_path": str(source_path),
                "dest_path": str(dest_path),
                "notes": row.get("notes", ""),
            })

    return added


def copy_hard_positives(selected_rows, output_dir):
    added = []
    tumor_dir = output_dir / "tumor"
    tumor_dir.mkdir(parents=True, exist_ok=True)

    for row in selected_rows:
        source_path = resolve_path(row.get("patch_path", ""))
        if source_path is None:
            raise FileNotFoundError(f"Patch hard-positive introuvable: {row.get('patch_path', '')}")

        dest_name = (
            f"iter5_hp_{row['slide_id']}_cand{int(row['candidate_id']):03d}_"
            f"{source_path.name}"
        )
        dest_path = tumor_dir / dest_name
        shutil.copy2(source_path, dest_path)
        added.append({
            "type": "hard_positive",
            "slide_id": row["slide_id"],
            "candidate_id": row["candidate_id"],
            "component_id": "",
            "review_category": row.get("review_category", ""),
            "difficulty_type": row.get("difficulty_type", ""),
            "source_path": str(source_path),
            "dest_path": str(dest_path),
            "notes": row.get("notes", ""),
        })

    return added


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, source_counts, output_counts, added_rows):
    hard_negatives = [row for row in added_rows if row["type"] == "hard_negative"]
    hard_positives = [row for row in added_rows if row["type"] == "hard_positive"]

    lines = [
        "# Iter5 Dataset Preparation",
        "",
        "`iter5` is built from `data/patches_iter2/train` plus reviewed iter4 false-positive hard negatives and iter2 hard-positive candidates.",
        "",
        "## Selection",
        "",
        "- Included hard negatives: `include_as_hard_negative=yes`",
        "- Included hard positives: `include_as_hard_positive=yes`",
        f"- Added hard-negative patches: {len(hard_negatives)}",
        f"- Added hard-positive patches: {len(hard_positives)}",
        "",
        "## Counts",
        "",
        "| Dataset | Normal | Tumor | Total |",
        "| --- | ---: | ---: | ---: |",
        f"| Source iter2 | {source_counts['normal']} | {source_counts['tumor']} | {source_counts['total']} |",
        f"| Iter5 | {output_counts['normal']} | {output_counts['tumor']} | {output_counts['total']} |",
        "",
        "## Added Hard-Negative Categories",
        "",
        "| Category | Added patches |",
        "| --- | ---: |",
    ]

    category_counts = {}
    for row in hard_negatives:
        category = row["review_category"] or "uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} |")

    lines.extend([
        "",
        "## Added Hard-Positive Categories",
        "",
        "| Category | Added patches |",
        "| --- | ---: |",
    ])

    category_counts = {}
    for row in hard_positives:
        category = row["review_category"] or "uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare iter5 training data from iter2 plus reviewed hard negatives and hard positives."
    )
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--fp-review-csv", default=str(FP_REVIEW_CSV))
    parser.add_argument("--hp-review-csv", default=str(HP_REVIEW_CSV))
    parser.add_argument("--summary-dir", default=str(SUMMARY_DIR))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rebuild output-dir if it already exists.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    fp_review_csv = Path(args.fp_review_csv)
    hp_review_csv = Path(args.hp_review_csv)
    summary_dir = Path(args.summary_dir)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source dataset introuvable: {source_dir}")
    if not fp_review_csv.exists():
        raise FileNotFoundError(f"Hard-negative review CSV introuvable: {fp_review_csv}")
    if not hp_review_csv.exists():
        raise FileNotFoundError(f"Hard-positive review CSV introuvable: {hp_review_csv}")

    source_counts = count_images(source_dir)
    selected_hn = read_selected_rows(fp_review_csv, "include_as_hard_negative")
    selected_hp = read_selected_rows(hp_review_csv, "include_as_hard_positive")

    copy_base_dataset(source_dir, output_dir, args.overwrite)
    added_rows = []
    added_rows.extend(copy_hard_negatives(selected_hn, output_dir))
    added_rows.extend(copy_hard_positives(selected_hp, output_dir))
    output_counts = count_images(output_dir)

    fieldnames = [
        "type",
        "slide_id",
        "candidate_id",
        "component_id",
        "review_category",
        "difficulty_type",
        "source_path",
        "dest_path",
        "notes",
    ]
    write_csv(summary_dir / "added_hard_examples.csv", added_rows, fieldnames)
    write_summary(summary_dir / "summary.md", source_counts, output_counts, added_rows)

    print("Source iter2:", source_counts)
    print("Iter5:", output_counts)
    print("Hard-negative rows selected:", len(selected_hn))
    print("Hard-positive rows selected:", len(selected_hp))
    print("Hard examples added:", len(added_rows))
    print("Dataset:", output_dir)
    print("Summary:", summary_dir / "summary.md")


if __name__ == "__main__":
    main()
