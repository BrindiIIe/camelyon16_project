from pathlib import Path
import argparse
import csv
from collections import deque


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data/inference_iter2"
OUTPUT_DIR = PROJECT_ROOT / "outputs/wsi_connected_components_iter2"

DEFAULT_SLIDES = [
    *[f"tumor_{i:03d}" for i in range(1, 11)],
    *[f"normal_{i:03d}" for i in range(1, 11)],
]


def true_label_from_slide(slide_id):
    if slide_id.startswith("tumor_"):
        return 1
    if slide_id.startswith("normal_"):
        return 0
    raise ValueError(f"Label inconnu pour slide: {slide_id}")


def read_probs(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "x": int(float(row["x"])),
                "y": int(float(row["y"])),
                "prob": float(row["prob_tumor"]),
            })
    return rows


def largest_connected_component(points, stride):
    if not points:
        return 0

    points = set(points)
    visited = set()
    largest = 0
    offsets = [
        (-stride, -stride), (0, -stride), (stride, -stride),
        (-stride, 0),                     (stride, 0),
        (-stride, stride),  (0, stride),  (stride, stride),
    ]

    for start in points:
        if start in visited:
            continue

        size = 0
        queue = deque([start])
        visited.add(start)

        while queue:
            x, y = queue.popleft()
            size += 1

            for dx, dy in offsets:
                neighbor = (x + dx, y + dy)
                if neighbor in points and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        largest = max(largest, size)

    return largest


def evaluate_slide(rows, patch_threshold, min_component_size, stride):
    probs = [row["prob"] for row in rows]
    positive_points = [
        (row["x"], row["y"])
        for row in rows
        if row["prob"] >= patch_threshold
    ]
    largest_component = largest_connected_component(positive_points, stride)

    return {
        "max_prob": max(probs) if probs else 0.0,
        "positive_patches": len(positive_points),
        "largest_component": largest_component,
        "pred_label": 1 if largest_component >= min_component_size else 0,
    }


def compute_summary(per_slide_rows):
    tp = sum(1 for r in per_slide_rows if r["true_label"] == 1 and r["pred_label"] == 1)
    fp = sum(1 for r in per_slide_rows if r["true_label"] == 0 and r["pred_label"] == 1)
    fn = sum(1 for r in per_slide_rows if r["true_label"] == 1 and r["pred_label"] == 0)
    tn = sum(1 for r in per_slide_rows if r["true_label"] == 0 and r["pred_label"] == 0)

    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precision * sensitivity / (precision + sensitivity)) if (precision + sensitivity) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
        "accuracy": accuracy,
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_table(path, rows):
    headers = [
        "Seuil patch",
        "Composante min",
        "Sensibilite",
        "Specificite",
        "Precision",
        "F1",
        "TP",
        "FP",
        "FN",
        "TN",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        values = [
            f"{row['patch_threshold']:.2f}",
            str(row["min_component_size"]),
            f"{row['sensitivity']:.3f}",
            f"{row['specificity']:.3f}",
            f"{row['precision']:.3f}",
            f"{row['f1']:.3f}",
            str(row["tp"]),
            str(row["fp"]),
            str(row["fn"]),
            str(row["tn"]),
        ]
        lines.append("| " + " | ".join(values) + " |")

    note = (
        "\n\nPrediction WSI positive si la plus grande composante connexe de "
        "patches positifs atteint la taille minimale indiquee."
    )
    path.write_text("\n".join(lines) + note + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate WSI-level detection using connected positive patch components."
    )
    parser.add_argument(
        "--csv-dir",
        default=str(CSV_DIR),
        help="Directory containing *_probs.csv inference files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory where WSI-level result tables are written.",
    )
    parser.add_argument(
        "--slides",
        nargs="+",
        default=DEFAULT_SLIDES,
        help="Slide ids without .tif suffix.",
    )
    parser.add_argument(
        "--patch-thresholds",
        nargs="+",
        type=float,
        default=[0.9, 0.8, 0.7, 0.6, 0.5],
        help="Patch probability thresholds.",
    )
    parser.add_argument(
        "--min-component-sizes",
        nargs="+",
        type=int,
        default=[10, 20, 30, 40, 50, 75, 100, 150, 200],
        help="Minimum connected component sizes in number of patches.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=128,
        help="Patch-grid stride used during WSI inference.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)

    slide_data = {}
    for slide_id in args.slides:
        csv_path = csv_dir / f"{slide_id}_probs.csv"
        if not csv_path.exists():
            print("CSV manquant, skip:", csv_path)
            continue
        slide_data[slide_id] = read_probs(csv_path)

    per_slide_all = []
    summary_rows = []

    for patch_threshold in args.patch_thresholds:
        for min_component_size in args.min_component_sizes:
            per_slide_rows = []

            for slide_id, rows in slide_data.items():
                metrics = evaluate_slide(
                    rows,
                    patch_threshold=patch_threshold,
                    min_component_size=min_component_size,
                    stride=args.stride,
                )
                row = {
                    "slide_id": slide_id,
                    "true_label": true_label_from_slide(slide_id),
                    "patch_threshold": patch_threshold,
                    "min_component_size": min_component_size,
                    **metrics,
                }
                per_slide_rows.append(row)
                per_slide_all.append(row)

            summary = compute_summary(per_slide_rows)
            summary_rows.append({
                "patch_threshold": patch_threshold,
                "min_component_size": min_component_size,
                "n_slides": len(per_slide_rows),
                **summary,
            })

    write_csv(
        output_dir / "per_slide_components.csv",
        per_slide_all,
        [
            "slide_id",
            "true_label",
            "patch_threshold",
            "min_component_size",
            "max_prob",
            "positive_patches",
            "largest_component",
            "pred_label",
        ],
    )
    write_csv(
        output_dir / "summary_components.csv",
        summary_rows,
        [
            "patch_threshold",
            "min_component_size",
            "n_slides",
            "sensitivity",
            "specificity",
            "precision",
            "f1",
            "accuracy",
            "tp",
            "fp",
            "fn",
            "tn",
        ],
    )
    write_markdown_table(output_dir / "manuscript_wsi_table.md", summary_rows)

    print(f"Slides evaluees: {len(slide_data)}")
    print("Resultats sauvegardes dans:", output_dir)


if __name__ == "__main__":
    main()
