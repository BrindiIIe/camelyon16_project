from pathlib import Path
import argparse
import csv
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data/patches_iter6/train"
OUTPUT_DIR = PROJECT_ROOT / "data/patches_iter7/train"
REVIEW_CSV = (
    PROJECT_ROOT
    / "portable_review_packs/iter6_clean_mask_unseen_train_fp_review/review_consensus.csv"
)
PATCH_ROOT = PROJECT_ROOT / "data/review/iter6_clean_mask_unseen_train_fp_components"
SPLIT_CSV = PROJECT_ROOT / "outputs/splits/wsi_split_v1.csv"
SUMMARY_DIR = PROJECT_ROOT / "outputs/iter7_dataset"
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
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    selected = []
    for row in rows:
        if row.get("include_as_hard_negative", "").strip().lower() != "yes":
            continue
        required = [
            "review_category",
            "binary_label",
            "morphology_category",
            "difficulty_type",
        ]
        missing = [field for field in required if not row.get(field, "").strip()]
        if missing:
            raise ValueError(
                f"Incomplete consensus for {row['slide_id']} component "
                f"{row['component_id']}: {missing}"
            )
        if row["binary_label"].strip().lower() != "normal":
            raise ValueError("Only consensus-normal patches may be injected as hard negatives.")
        selected.append(row)
    if not selected:
        raise ValueError("No consensus hard-negative rows selected.")
    return selected


def validate_train_slides(rows, split_csv):
    with open(split_csv, "r", newline="", encoding="utf-8-sig") as handle:
        split_by_slide = {row["slide_id"]: row["split"] for row in csv.DictReader(handle)}
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
                f"{output_dir} already exists. Use --overwrite to rebuild iter7."
            )
        shutil.rmtree(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, output_dir, ignore=shutil.ignore_patterns("._*", "__pycache__"))


def select_sources(rows, patch_root, patches_per_component, max_patches_per_slide):
    by_slide = {}
    for row in rows:
        component_id = int(row["component_id"])
        component_dir = patch_root / row["slide_id"] / f"component_{component_id:02d}"
        if not component_dir.exists():
            raise FileNotFoundError(component_dir)
        available = sorted(path for path in component_dir.iterdir() if is_patch_file(path))
        if len(available) < patches_per_component:
            raise ValueError(
                f"{row['slide_id']} component {component_id}: "
                f"{len(available)} available, {patches_per_component} required."
            )
        by_slide.setdefault(row["slide_id"], []).append((row, available))

    selected = []
    for slide_id in sorted(by_slide):
        components = sorted(by_slide[slide_id], key=lambda item: int(item[0]["component_id"]))
        # Round-robin ranks preserve component diversity when the per-slide cap is reached.
        for rank_index in range(patches_per_component):
            for row, available in components:
                if sum(1 for item in selected if item[0]["slide_id"] == slide_id) >= max_patches_per_slide:
                    break
                selected.append((row, available[rank_index], rank_index + 1))
    return selected


def copy_selected(selected, output_dir):
    added = []
    normal_dir = output_dir / "normal"
    normal_dir.mkdir(parents=True, exist_ok=True)
    for row, source_path, rank in selected:
        component_id = int(row["component_id"])
        dest_name = (
            f"iter7_hn_{row['slide_id']}_c{component_id:02d}_r{rank:02d}_"
            f"{source_path.name}"
        )
        dest_path = normal_dir / dest_name
        if dest_path.exists():
            raise FileExistsError(dest_path)
        shutil.copy2(source_path, dest_path)
        added.append(
            {
                "slide_id": row["slide_id"],
                "component_id": row["component_id"],
                "review_category": row["review_category"],
                "selection_rank": rank,
                "source_path": str(source_path),
                "dest_path": str(dest_path),
            }
        )
    return added


def write_outputs(summary_dir, added, source_counts, output_counts, component_cap, slide_cap):
    summary_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "slide_id",
        "component_id",
        "review_category",
        "selection_rank",
        "source_path",
        "dest_path",
    ]
    with open(summary_dir / "added_hard_negatives.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(added)

    category_counts = {}
    slide_counts = {}
    for row in added:
        category_counts[row["review_category"]] = category_counts.get(row["review_category"], 0) + 1
        slide_counts[row["slide_id"]] = slide_counts.get(row["slide_id"], 0) + 1
    lines = [
        "# Iter7 Dataset Preparation",
        "",
        "`iter7` is cumulative: `iter6` plus hard negatives from the corrected iter6 clean-mask consensus.",
        "",
        "## Selection contract",
        "",
        "- Source dataset: `data/patches_iter6/train`",
        "- Review source: corrected clean-mask `review_consensus.csv`",
        "- Required decision: `include_as_hard_negative=yes` and `binary_label=normal`",
        f"- Maximum patches per component: {component_cap}",
        f"- Maximum new patches per WSI: {slide_cap}",
        "- Allocation: deterministic rank round-robin across components",
        f"- New hard-negative patches: {len(added)}",
        "",
        "## Dataset counts",
        "",
        "| Dataset | Normal | Tumor | Total |",
        "| --- | ---: | ---: | ---: |",
        f"| Source iter6 | {source_counts['normal']} | {source_counts['tumor']} | {source_counts['total']} |",
        f"| Iter7 | {output_counts['normal']} | {output_counts['tumor']} | {output_counts['total']} |",
        "",
        "## Added patches by WSI",
        "",
        "| WSI | Patches |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {slide} | {count} |" for slide, count in sorted(slide_counts.items()))
    lines.extend(["", "## Added patches by morphology", "", "| Category | Patches |", "| --- | ---: |"])
    lines.extend(f"| {category} | {count} |" for category, count in sorted(category_counts.items()))
    (summary_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare iter7 from iter6 and corrected reviewed hard negatives.")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--review-csv", default=str(REVIEW_CSV))
    parser.add_argument("--patch-root", default=str(PATCH_ROOT))
    parser.add_argument("--split-csv", default=str(SPLIT_CSV))
    parser.add_argument("--summary-dir", default=str(SUMMARY_DIR))
    parser.add_argument("--patches-per-component", type=int, default=4)
    parser.add_argument("--max-patches-per-slide", type=int, default=64)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = read_selected_rows(Path(args.review_csv))
    validate_train_slides(rows, Path(args.split_csv))
    selected = select_sources(
        rows,
        Path(args.patch_root),
        args.patches_per_component,
        args.max_patches_per_slide,
    )
    source_counts = count_images(Path(args.source_dir))
    copy_base_dataset(Path(args.source_dir), Path(args.output_dir), args.overwrite)
    added = copy_selected(selected, Path(args.output_dir))
    output_counts = count_images(Path(args.output_dir))
    if output_counts["normal"] != source_counts["normal"] + len(added):
        raise RuntimeError("Unexpected iter7 normal-patch count.")
    if output_counts["tumor"] != source_counts["tumor"]:
        raise RuntimeError("Tumor-patch count changed while preparing iter7.")
    write_outputs(
        Path(args.summary_dir),
        added,
        source_counts,
        output_counts,
        args.patches_per_component,
        args.max_patches_per_slide,
    )
    print("Source iter6:", source_counts)
    print("Iter7:", output_counts)
    print("Reviewed components:", len(rows))
    print("Added hard negatives:", len(added))
    print("Dataset:", args.output_dir)


if __name__ == "__main__":
    main()
