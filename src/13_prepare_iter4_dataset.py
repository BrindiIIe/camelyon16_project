from pathlib import Path
import argparse
import csv
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data/patches_iter2/train"
OUTPUT_DIR = PROJECT_ROOT / "data/patches_iter4/train"
REVIEW_CSV = PROJECT_ROOT / "outputs/micro_fp_review_iter2/review_template.csv"
SUMMARY_DIR = PROJECT_ROOT / "outputs/iter4_dataset"

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}


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


def read_review_rows(review_csv, include_maybe):
    selected = []
    with open(review_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = row["include_as_hard_negative"].strip().lower()
            if decision == "yes" or (include_maybe and decision == "maybe"):
                selected.append(row)
    return selected


def copy_base_dataset(source_dir, output_dir, overwrite):
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"{output_dir} existe deja. Relancer avec --overwrite pour reconstruire iter4."
            )
        shutil.rmtree(output_dir)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_dir,
        output_dir,
        ignore=shutil.ignore_patterns("._*", "__pycache__"),
    )


def copy_selected_hard_negatives(selected_rows, output_dir):
    added = []
    normal_dir = output_dir / "normal"
    normal_dir.mkdir(parents=True, exist_ok=True)

    for row in selected_rows:
        patch_dir = Path(row["contact_sheet"]).parent
        source_patches = sorted(
            path
            for path in patch_dir.iterdir()
            if path.is_file() and is_patch_file(path)
        )

        for source_path in source_patches:
            dest_name = (
                f"iter4_micro_fp_{row['slide_id']}_c{int(row['component_id']):02d}_"
                f"{source_path.name}"
            )
            dest_path = normal_dir / dest_name
            shutil.copy2(source_path, dest_path)
            added.append({
                "slide_id": row["slide_id"],
                "component_id": row["component_id"],
                "decision": row["include_as_hard_negative"],
                "review_category": row["review_category"],
                "source_path": str(source_path),
                "dest_path": str(dest_path),
                "notes": row["notes"],
            })

    return added


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, source_counts, output_counts, added_rows, include_maybe):
    lines = [
        "# Iter4 Dataset Preparation",
        "",
        "`iter4` is built from `data/patches_iter2/train` plus reviewed micro false-positive hard negatives.",
        "",
        "## Selection",
        "",
        f"- Included `yes` decisions: always",
        f"- Included `maybe` decisions: {'yes' if include_maybe else 'no'}",
        f"- Added hard-negative patches: {len(added_rows)}",
        "",
        "## Counts",
        "",
        "| Dataset | Normal | Tumor | Total |",
        "| --- | ---: | ---: | ---: |",
        f"| Source iter2 | {source_counts['normal']} | {source_counts['tumor']} | {source_counts['total']} |",
        f"| Iter4 | {output_counts['normal']} | {output_counts['tumor']} | {output_counts['total']} |",
        "",
        "## Added Components",
        "",
        "| Slide | Component | Decision | Category | Added patches |",
        "| --- | ---: | --- | --- | ---: |",
    ]

    grouped = {}
    for row in added_rows:
        key = (row["slide_id"], row["component_id"], row["decision"], row["review_category"])
        grouped[key] = grouped.get(key, 0) + 1

    for (slide_id, component_id, decision, category), n_patches in sorted(grouped.items()):
        lines.append(
            f"| {slide_id} | {component_id} | {decision} | {category} | {n_patches} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare iter4 training data from iter2 plus reviewed micro false-positive hard negatives."
    )
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--review-csv", default=str(REVIEW_CSV))
    parser.add_argument("--summary-dir", default=str(SUMMARY_DIR))
    parser.add_argument(
        "--include-maybe",
        action="store_true",
        help="Also include rows marked maybe in the review table.",
    )
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
    review_csv = Path(args.review_csv)
    summary_dir = Path(args.summary_dir)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source dataset introuvable: {source_dir}")
    if not review_csv.exists():
        raise FileNotFoundError(f"Review CSV introuvable: {review_csv}")

    source_counts = count_images(source_dir)
    selected_rows = read_review_rows(review_csv, args.include_maybe)

    copy_base_dataset(source_dir, output_dir, args.overwrite)
    added_rows = copy_selected_hard_negatives(selected_rows, output_dir)
    output_counts = count_images(output_dir)

    write_csv(
        summary_dir / "added_hard_negatives.csv",
        added_rows,
        [
            "slide_id",
            "component_id",
            "decision",
            "review_category",
            "source_path",
            "dest_path",
            "notes",
        ],
    )
    write_summary(
        summary_dir / "summary.md",
        source_counts,
        output_counts,
        added_rows,
        args.include_maybe,
    )

    print("Source iter2:", source_counts)
    print("Iter4:", output_counts)
    print("Hard-negative patches added:", len(added_rows))
    print("Dataset:", output_dir)
    print("Summary:", summary_dir / "summary.md")


if __name__ == "__main__":
    main()
