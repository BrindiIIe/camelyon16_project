from pathlib import Path
import argparse
import csv
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLIT_CSV = PROJECT_ROOT / "outputs/splits/wsi_split_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/inference_queues"


def read_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def slide_sort_key(row):
    slide_id = row["slide_id"]
    prefix, number = slide_id.split("_", 1)
    return prefix, int(number)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a resumable WSI inference queue from the slide-level split."
    )
    parser.add_argument("--split-csv", default=str(SPLIT_CSV))
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--experiment", required=True, help="Model/run name, e.g. iter2.")
    parser.add_argument("--purpose", required=True, help="Run purpose, e.g. hard_negative_screen.")
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train"],
        help="Allowed split values from wsi_split_v1.csv.",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        default=["normal"],
        help="Allowed labels: normal and/or tumor.",
    )
    parser.add_argument(
        "--include-hard-mined",
        action="store_true",
        help="Include slides already marked as used_for_hard_mining=yes.",
    )
    parser.add_argument(
        "--include-prior-exploration",
        action="store_true",
        help="Include slides already used in prior WSI exploration.",
    )
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    split_rows = read_rows(Path(args.split_csv))
    allowed_splits = set(args.splits)
    allowed_labels = set(args.labels)

    selected = []
    for row in sorted(split_rows, key=slide_sort_key):
        if row["split"] not in allowed_splits:
            continue
        if row["label"] not in allowed_labels:
            continue
        if row["split"] == "test_final":
            continue
        if row["used_for_hard_mining"] == "yes" and not args.include_hard_mined:
            continue
        if row["used_for_prior_wsi_exploration"] == "yes" and not args.include_prior_exploration:
            continue
        selected.append(row)

    if args.limit is not None:
        selected = selected[:args.limit]

    created_at = datetime.now().isoformat(timespec="seconds")
    queue_rows = []
    for idx, row in enumerate(selected, start=1):
        queue_rows.append({
            "queue_index": idx,
            "slide_id": row["slide_id"],
            "slide_filename": f"{row['slide_id']}.tif",
            "label": row["label"],
            "split": row["split"],
            "experiment": args.experiment,
            "purpose": args.purpose,
            "wsi_path": row["wsi_path"],
            "annotation_path": row["annotation_path"],
            "used_for_hard_mining": row["used_for_hard_mining"],
            "hard_mining_role": row["hard_mining_role"],
            "status": "pending",
            "attempts": 0,
            "created_at": created_at,
            "started_at": "",
            "finished_at": "",
            "seconds": "",
            "n_patches": "",
            "output_csv": "",
            "notes": "",
        })

    fieldnames = [
        "queue_index",
        "slide_id",
        "slide_filename",
        "label",
        "split",
        "experiment",
        "purpose",
        "wsi_path",
        "annotation_path",
        "used_for_hard_mining",
        "hard_mining_role",
        "status",
        "attempts",
        "created_at",
        "started_at",
        "finished_at",
        "seconds",
        "n_patches",
        "output_csv",
        "notes",
    ]

    output_path = Path(args.output_csv)
    if not output_path.is_absolute():
        output_path = OUTPUT_DIR / output_path
    write_csv(output_path, queue_rows, fieldnames)

    print("Queue:", output_path)
    print("Slides:", len(queue_rows))


if __name__ == "__main__":
    main()

