from pathlib import Path
import argparse
import csv
from collections import deque


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data/inference_iter2"
OUTPUT_DIR = PROJECT_ROOT / "outputs/wsi_hybrid_rules_iter2"

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

        queue = deque([start])
        visited.add(start)
        size = 0

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


def component_stats(rows, threshold, stride):
    positive_points = [
        (row["x"], row["y"])
        for row in rows
        if row["prob"] >= threshold
    ]
    return {
        "positive_patches": len(positive_points),
        "largest_component": largest_connected_component(positive_points, stride),
    }


def compute_summary(rows):
    tp = sum(1 for r in rows if r["true_label"] == 1 and r["pred_label"] == 1)
    fp = sum(1 for r in rows if r["true_label"] == 0 and r["pred_label"] == 1)
    fn = sum(1 for r in rows if r["true_label"] == 1 and r["pred_label"] == 0)
    tn = sum(1 for r in rows if r["true_label"] == 0 and r["pred_label"] == 0)

    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precision * sensitivity / (precision + sensitivity)) if (precision + sensitivity) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0

    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
        "accuracy": accuracy,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, rows):
    ranked = sorted(
        rows,
        key=lambda r: (r["f1"], r["sensitivity"], r["specificity"], r["precision"]),
        reverse=True,
    )
    headers = [
        "Regle",
        "Large thr",
        "Large min",
        "Micro thr",
        "Micro min",
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

    for row in ranked[:30]:
        values = [
            row["rule"],
            f"{row['large_threshold']:.2f}",
            str(row["large_min_component"]),
            f"{row['micro_threshold']:.2f}",
            str(row["micro_min_component"]),
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
        "\n\n`large_component`: positive si une composante moderee est assez grande. "
        "`micro_cluster`: positive si un petit cluster de haute confiance existe. "
        "`hybrid`: positive si au moins une des deux regles est positive."
    )
    path.write_text("\n".join(lines) + note + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate WSI-level large-lesion, micro-cluster, and hybrid rules."
    )
    parser.add_argument("--csv-dir", default=str(CSV_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--slides", nargs="+", default=DEFAULT_SLIDES)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--large-thresholds", nargs="+", type=float, default=[0.6, 0.5])
    parser.add_argument("--large-min-components", nargs="+", type=int, default=[30, 40, 50])
    parser.add_argument("--micro-thresholds", nargs="+", type=float, default=[0.99, 0.98, 0.95])
    parser.add_argument("--micro-min-components", nargs="+", type=int, default=[2, 3, 5])
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

    per_slide_rows = []
    summary_rows = []

    for large_threshold in args.large_thresholds:
        for large_min in args.large_min_components:
            for micro_threshold in args.micro_thresholds:
                for micro_min in args.micro_min_components:
                    grouped = {
                        "large_component": [],
                        "micro_cluster": [],
                        "hybrid": [],
                    }

                    for slide_id, rows in slide_data.items():
                        large = component_stats(rows, large_threshold, args.stride)
                        micro = component_stats(rows, micro_threshold, args.stride)

                        large_pred = int(large["largest_component"] >= large_min)
                        micro_pred = int(micro["largest_component"] >= micro_min)
                        preds = {
                            "large_component": large_pred,
                            "micro_cluster": micro_pred,
                            "hybrid": int(large_pred or micro_pred),
                        }

                        for rule, pred_label in preds.items():
                            row = {
                                "slide_id": slide_id,
                                "true_label": true_label_from_slide(slide_id),
                                "rule": rule,
                                "large_threshold": large_threshold,
                                "large_min_component": large_min,
                                "micro_threshold": micro_threshold,
                                "micro_min_component": micro_min,
                                "large_positive_patches": large["positive_patches"],
                                "large_largest_component": large["largest_component"],
                                "micro_positive_patches": micro["positive_patches"],
                                "micro_largest_component": micro["largest_component"],
                                "pred_label": pred_label,
                            }
                            grouped[rule].append(row)
                            per_slide_rows.append(row)

                    for rule, rows_for_rule in grouped.items():
                        summary = compute_summary(rows_for_rule)
                        summary_rows.append({
                            "rule": rule,
                            "large_threshold": large_threshold,
                            "large_min_component": large_min,
                            "micro_threshold": micro_threshold,
                            "micro_min_component": micro_min,
                            "n_slides": len(rows_for_rule),
                            **summary,
                        })

    write_csv(
        output_dir / "per_slide_hybrid_rules.csv",
        per_slide_rows,
        [
            "slide_id",
            "true_label",
            "rule",
            "large_threshold",
            "large_min_component",
            "micro_threshold",
            "micro_min_component",
            "large_positive_patches",
            "large_largest_component",
            "micro_positive_patches",
            "micro_largest_component",
            "pred_label",
        ],
    )
    write_csv(
        output_dir / "summary_hybrid_rules.csv",
        summary_rows,
        [
            "rule",
            "large_threshold",
            "large_min_component",
            "micro_threshold",
            "micro_min_component",
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
    write_markdown(output_dir / "manuscript_hybrid_rules.md", summary_rows)

    print(f"Slides evaluees: {len(slide_data)}")
    print("Resultats sauvegardes dans:", output_dir)


if __name__ == "__main__":
    main()
