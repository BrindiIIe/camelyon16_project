from pathlib import Path
import argparse
import csv
import random
from collections import Counter, defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WSI_DIR = PROJECT_ROOT / "data/wsi"
ANNOTATION_DIR = PROJECT_ROOT / "data/annotations"
OUTPUT_DIR = PROJECT_ROOT / "outputs/splits"

REVIEW_FILES = [
    {
        "path": PROJECT_ROOT / "outputs/micro_fp_review_iter2/review_template.csv",
        "role": "micro_fp_hard_negative_review",
        "slide_column": "slide_id",
    },
    {
        "path": PROJECT_ROOT / "outputs/iter4_fp_review/review_template.csv",
        "role": "iter4_fp_hard_negative_review",
        "slide_column": "slide_id",
    },
    {
        "path": PROJECT_ROOT / "outputs/hard_positive_review_iter2/review_template.csv",
        "role": "iter2_hard_positive_review",
        "slide_column": "slide_id",
    },
]

PRIOR_WSI_EVAL_SLIDES = {
    *[f"tumor_{idx:03d}" for idx in range(1, 11)],
    *[f"normal_{idx:03d}" for idx in range(1, 11)],
}


def slide_sort_key(slide_id):
    prefix, number = slide_id.split("_", 1)
    return prefix, int(number)


def read_review_usage():
    roles_by_slide = defaultdict(set)

    for review in REVIEW_FILES:
        path = review["path"]
        if not path.exists():
            continue

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slide_id = row.get(review["slide_column"], "").strip()
                if slide_id:
                    roles_by_slide[slide_id].add(review["role"])

    for slide_id in PRIOR_WSI_EVAL_SLIDES:
        roles_by_slide[slide_id].add("prior_20_wsi_exploration")

    return roles_by_slide


def label_from_slide(slide_id, has_annotation):
    if slide_id.startswith("normal_"):
        return "normal", "prefix"
    if slide_id.startswith("tumor_"):
        return "tumor", "prefix"
    if slide_id.startswith("test_"):
        return ("tumor", "test_xml_present") if has_annotation else ("normal", "test_no_xml_assumed_normal")
    return "unknown", "unknown"


def build_inventory(wsi_dir, annotation_dir, roles_by_slide):
    wsi_files = {
        path.stem: path
        for path in wsi_dir.glob("*.tif")
        if path.is_file() and not path.name.startswith("._")
    }
    xml_files = {
        path.stem: path
        for path in annotation_dir.glob("*.xml")
        if path.is_file() and not path.name.startswith("._")
    }

    rows = []
    for slide_id, wsi_path in sorted(wsi_files.items(), key=lambda item: slide_sort_key(item[0])):
        has_annotation = slide_id in xml_files
        label, label_source = label_from_slide(slide_id, has_annotation)
        roles = sorted(roles_by_slide.get(slide_id, []))
        hard_roles = [role for role in roles if "hard_" in role or "fp_" in role]

        rows.append({
            "slide_id": slide_id,
            "label": label,
            "label_source": label_source,
            "wsi_path": str(wsi_path),
            "wsi_exists": "yes",
            "wsi_size_bytes": str(wsi_path.stat().st_size),
            "annotation_path": str(xml_files[slide_id]) if has_annotation else "",
            "has_annotation": "yes" if has_annotation else "no",
            "used_for_hard_mining": "yes" if hard_roles else "no",
            "hard_mining_role": ";".join(hard_roles),
            "used_for_prior_wsi_exploration": "yes" if "prior_20_wsi_exploration" in roles else "no",
            "all_roles": ";".join(roles),
            "notes": "",
        })

    return rows, wsi_files, xml_files


def assign_split(inventory_rows, val_fraction, seed):
    rows = [dict(row) for row in inventory_rows]

    for row in rows:
        slide_id = row["slide_id"]
        if row["label"] == "unknown":
            row["split"] = "exclude"
            row["split_reason"] = "unknown_label"
        elif row["used_for_hard_mining"] == "yes":
            row["split"] = "train"
            row["split_reason"] = "used_for_hard_mining"
        elif slide_id.startswith("test_"):
            row["split"] = "test_final"
            row["split_reason"] = "official_test_set_not_used_for_hard_mining"
        elif row["used_for_prior_wsi_exploration"] == "yes":
            row["split"] = "train"
            row["split_reason"] = "prior_wsi_exploration"
        else:
            row["split"] = ""
            row["split_reason"] = ""

    rng = random.Random(seed)
    candidates_by_label = defaultdict(list)
    for row in rows:
        if row["split"]:
            continue
        candidates_by_label[row["label"]].append(row["slide_id"])

    val_slide_ids = set()
    for label, slide_ids in candidates_by_label.items():
        shuffled = sorted(slide_ids, key=slide_sort_key)
        rng.shuffle(shuffled)
        n_val = max(1, round(len(shuffled) * val_fraction)) if shuffled else 0
        val_slide_ids.update(shuffled[:n_val])

    for row in rows:
        if row["split"]:
            continue
        if row["slide_id"] in val_slide_ids:
            row["split"] = "val"
            row["split_reason"] = "stratified_slide_level_validation"
        else:
            row["split"] = "train"
            row["split_reason"] = "stratified_slide_level_training"

    return rows


def missing_number_summary(wsi_files):
    expected = {
        "normal": range(1, 157),
        "tumor": range(1, 112),
        "test": range(1, 131),
    }
    missing = {}
    for prefix, numbers in expected.items():
        present = {
            int(slide_id.split("_", 1)[1])
            for slide_id in wsi_files
            if slide_id.startswith(f"{prefix}_")
        }
        missing[prefix] = [f"{prefix}_{idx:03d}" for idx in numbers if idx not in present]
    return missing


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, inventory_rows, split_rows, wsi_files, xml_files):
    inventory_counts = Counter(row["slide_id"].split("_", 1)[0] for row in inventory_rows)
    label_counts = Counter(row["label"] for row in inventory_rows)
    split_label_counts = Counter((row["split"], row["label"]) for row in split_rows)
    hard_rows = [row for row in split_rows if row["used_for_hard_mining"] == "yes"]
    test_rows = [row for row in split_rows if row["split"] == "test_final"]
    missing = missing_number_summary(wsi_files)

    xml_without_wsi = sorted(set(xml_files) - set(wsi_files), key=slide_sort_key)

    lines = [
        "# WSI Split v1 Summary",
        "",
        "This split is slide-level: every WSI belongs to exactly one split.",
        "Slides used for hard mining are forced into `train` and excluded from the final test set.",
        "",
        "## Inventory",
        "",
        "| Group | WSI count |",
        "| --- | ---: |",
    ]
    for group in ["normal", "tumor", "test"]:
        lines.append(f"| {group} | {inventory_counts[group]} |")

    lines.extend([
        "",
        "| Label | WSI count |",
        "| --- | ---: |",
    ])
    for label, count in sorted(label_counts.items()):
        lines.append(f"| {label} | {count} |")

    lines.extend([
        "",
        "For `test_*` slides, labels are inferred from XML availability: XML present = tumor, no XML = assumed normal.",
        "",
        "## Split Counts",
        "",
        "| Split | Normal | Tumor | Total |",
        "| --- | ---: | ---: | ---: |",
    ])

    for split in ["train", "val", "test_final", "exclude"]:
        normal = split_label_counts[(split, "normal")]
        tumor = split_label_counts[(split, "tumor")]
        total = normal + tumor + split_label_counts[(split, "unknown")]
        if total:
            lines.append(f"| {split} | {normal} | {tumor} | {total} |")

    lines.extend([
        "",
        "## Hard-Mining / Prior-Use Slides",
        "",
        f"Slides marked as used for hard mining: `{len(hard_rows)}`.",
        "",
        "| Slide | Label | Split | Hard-mining role | Other roles |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in sorted(hard_rows, key=lambda item: slide_sort_key(item["slide_id"])):
        lines.append(
            f"| {row['slide_id']} | {row['label']} | {row['split']} | "
            f"{row['hard_mining_role']} | {row['all_roles']} |"
        )

    lines.extend([
        "",
        "## Final Test Set",
        "",
        f"Final test candidates: `{len(test_rows)}` WSI.",
        f"- Normal: `{sum(1 for row in test_rows if row['label'] == 'normal')}`",
        f"- Tumor: `{sum(1 for row in test_rows if row['label'] == 'tumor')}`",
        "",
        "No slide currently marked as hard-mining material is assigned to `test_final`.",
        "",
        "## Missing / Extra Files",
        "",
        "| Expected group | Missing WSI IDs |",
        "| --- | --- |",
    ])
    for group in ["normal", "tumor", "test"]:
        value = ", ".join(missing[group]) if missing[group] else "none"
        lines.append(f"| {group} | {value} |")

    lines.extend([
        "",
        "XML files without a matching root-level WSI:",
        "",
        ", ".join(xml_without_wsi) if xml_without_wsi else "none",
        "",
        "## Recommended Use",
        "",
        "- Use `train` for patch extraction, model training, and hard-example enrichment.",
        "- Use `val` to tune model thresholds and WSI connected-component rules.",
        "- Use `test_final` only once the pipeline and thresholds are frozen.",
    ])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Create a slide-level CAMELYON16 WSI inventory and split.")
    parser.add_argument("--wsi-dir", default=str(WSI_DIR))
    parser.add_argument("--annotation-dir", default=str(ANNOTATION_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    wsi_dir = Path(args.wsi_dir)
    annotation_dir = Path(args.annotation_dir)
    output_dir = Path(args.output_dir)

    roles_by_slide = read_review_usage()
    inventory_rows, wsi_files, xml_files = build_inventory(wsi_dir, annotation_dir, roles_by_slide)
    split_rows = assign_split(inventory_rows, args.val_fraction, args.seed)

    inventory_fields = [
        "slide_id",
        "label",
        "label_source",
        "wsi_path",
        "wsi_exists",
        "wsi_size_bytes",
        "annotation_path",
        "has_annotation",
        "used_for_hard_mining",
        "hard_mining_role",
        "used_for_prior_wsi_exploration",
        "all_roles",
        "notes",
    ]
    split_fields = [
        "slide_id",
        "label",
        "split",
        "split_reason",
        "label_source",
        "has_annotation",
        "used_for_hard_mining",
        "hard_mining_role",
        "used_for_prior_wsi_exploration",
        "all_roles",
        "wsi_path",
        "annotation_path",
        "notes",
    ]

    write_csv(output_dir / "wsi_inventory_v1.csv", inventory_rows, inventory_fields)
    write_csv(output_dir / "wsi_split_v1.csv", split_rows, split_fields)
    write_summary(output_dir / "wsi_split_v1_summary.md", inventory_rows, split_rows, wsi_files, xml_files)

    print("Inventory:", output_dir / "wsi_inventory_v1.csv")
    print("Split:", output_dir / "wsi_split_v1.csv")
    print("Summary:", output_dir / "wsi_split_v1_summary.md")


if __name__ == "__main__":
    main()
