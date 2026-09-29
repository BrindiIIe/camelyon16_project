from pathlib import Path
import argparse
import csv
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data/patches_iter2/train"
OUTPUT_DIR = PROJECT_ROOT / "data/patches_iter6/train"
REVIEW_CSV = PROJECT_ROOT / "outputs/iter5_hn_train_fp_review/review_template.csv"
PATCH_ROOT = PROJECT_ROOT / "data/review/iter5_hn_train_fp_components"
SPLIT_CSV = PROJECT_ROOT / "outputs/splits/wsi_split_v1.csv"
SUMMARY_DIR = PROJECT_ROOT / "outputs/iter6_dataset"
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def is_patch_file(path):
    return (
        path.is_file()
        and not path.name.startswith("._")
        and path.suffix.lower() in VALID_EXTENSIONS
        and "contact_sheet" not in path.name
        and "overview" not in path.name
    )


def count_images(folder):
    counts = {}
    for label in ["normal", "tumor"]:
        label_dir = folder / label
        counts[label] = (
            sum(1 for path in label_dir.iterdir() if is_patch_file(path))
            if label_dir.exists()
            else 0
        )
    counts["total"] = counts["normal"] + counts["tumor"]
    return counts


def read_selected_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        return [
            row
            for row in csv.DictReader(f)
            if row.get("include_as_hard_negative", "").strip().lower() == "yes"
        ]


def validate_train_slides(rows, split_csv):
    with open(split_csv, "r", newline="", encoding="utf-8") as f:
        split_by_slide = {row["slide_id"]: row["split"] for row in csv.DictReader(f)}

    invalid = {
        row["slide_id"]: split_by_slide.get(row["slide_id"], "missing")
        for row in rows
        if split_by_slide.get(row["slide_id"]) != "train"
    }
    if invalid:
        raise ValueError(f"Hard-negative slides must all be in train: {invalid}")


def copy_base_dataset(source_dir, output_dir, overwrite):
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"{output_dir} existe deja. Utiliser --overwrite pour reconstruire iter6."
            )
        shutil.rmtree(output_dir)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_dir,
        output_dir,
        ignore=shutil.ignore_patterns("._*", "__pycache__"),
    )


def copy_hard_negatives(rows, patch_root, output_dir, patches_per_component):
    added = []
    normal_dir = output_dir / "normal"
    normal_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        component_id = int(row["component_id"])
        component_dir = patch_root / row["slide_id"] / f"component_{component_id:02d}"
        available = sorted(path for path in component_dir.iterdir() if is_patch_file(path))
        if len(available) < patches_per_component:
            raise ValueError(
                f"{row['slide_id']} component {component_id}: "
                f"{len(available)} patches disponibles, {patches_per_component} requis."
            )

        # Files are ranked p01, p02, ... by decreasing model probability.
        selected = available[:patches_per_component]
        for rank, source_path in enumerate(selected, start=1):
            dest_name = (
                f"iter6_hn_{row['slide_id']}_c{component_id:02d}_r{rank:02d}_"
                f"{source_path.name}"
            )
            dest_path = normal_dir / dest_name
            shutil.copy2(source_path, dest_path)
            added.append(
                {
                    "slide_id": row["slide_id"],
                    "component_id": row["component_id"],
                    "review_category": row.get("review_category", ""),
                    "selection_rank": rank,
                    "source_path": str(source_path),
                    "dest_path": str(dest_path),
                }
            )
    return added


def write_csv(path, rows):
    fieldnames = [
        "slide_id",
        "component_id",
        "review_category",
        "selection_rank",
        "source_path",
        "dest_path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, source_counts, output_counts, rows, patches_per_component):
    category_counts = {}
    for row in rows:
        category = row["review_category"] or "uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1

    components = {(row["slide_id"], row["component_id"]) for row in rows}
    slides = {row["slide_id"] for row in rows}
    lines = [
        "# Iter6 Dataset Preparation",
        "",
        "`iter6` is built from `data/patches_iter2/train` plus the newly reviewed iter5 false-positive hard negatives.",
        "",
        "## Selection",
        "",
        "- Reference dataset: `iter2`",
        "- Included review decision: `include_as_hard_negative=yes`",
        f"- Source slides: {len(slides)} (all checked as `train`)",
        f"- Reviewed components: {len(components)}",
        f"- Patches per component: {patches_per_component}",
        f"- Added hard-negative patches: {len(rows)}",
        "",
        "## Counts",
        "",
        "| Dataset | Normal | Tumor | Total |",
        "| --- | ---: | ---: | ---: |",
        f"| Source iter2 | {source_counts['normal']} | {source_counts['tumor']} | {source_counts['total']} |",
        f"| Iter6 | {output_counts['normal']} | {output_counts['tumor']} | {output_counts['total']} |",
        "",
        "## Added Hard-Negative Categories",
        "",
        "| Category | Added patches |",
        "| --- | ---: |",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare iter6 from iter2 plus reviewed FP hard negatives."
    )
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--review-csv", default=str(REVIEW_CSV))
    parser.add_argument("--patch-root", default=str(PATCH_ROOT))
    parser.add_argument("--split-csv", default=str(SPLIT_CSV))
    parser.add_argument("--summary-dir", default=str(SUMMARY_DIR))
    parser.add_argument("--patches-per-component", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    review_csv = Path(args.review_csv)
    patch_root = Path(args.patch_root)
    split_csv = Path(args.split_csv)
    summary_dir = Path(args.summary_dir)

    rows = read_selected_rows(review_csv)
    validate_train_slides(rows, split_csv)
    source_counts = count_images(source_dir)
    copy_base_dataset(source_dir, output_dir, args.overwrite)
    added = copy_hard_negatives(
        rows, patch_root, output_dir, args.patches_per_component
    )
    output_counts = count_images(output_dir)

    expected = len(rows) * args.patches_per_component
    if len(added) != expected or output_counts["normal"] != source_counts["normal"] + expected:
        raise RuntimeError("Unexpected iter6 hard-negative count after dataset preparation.")

    write_csv(summary_dir / "added_hard_negatives.csv", added)
    write_summary(
        summary_dir / "summary.md",
        source_counts,
        output_counts,
        added,
        args.patches_per_component,
    )
    print("Source iter2:", source_counts)
    print("Iter6:", output_counts)
    print("Selected components:", len(rows))
    print("Added hard negatives:", len(added))
    print("Dataset:", output_dir)


if __name__ == "__main__":
    main()
