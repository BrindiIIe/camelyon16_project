from pathlib import Path
import argparse
import csv
from collections import Counter

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPERIMENTS = [
    {
        "name": "baseline",
        "train_dir": PROJECT_ROOT / "data/patches_base/train",
        "checkpoints": [
            PROJECT_ROOT / "models/best_resnet18_patch_baseline.pt",
            PROJECT_ROOT / "models/baseline/best_resnet18_patch.pt",
        ],
    },
    {
        "name": "iter1",
        "train_dir": PROJECT_ROOT / "data/patches_iter1/train",
        "checkpoints": [
            PROJECT_ROOT / "models/best_resnet18_patch_iter1.pt",
            PROJECT_ROOT / "models/iter1/best_resnet18_patch.pt",
        ],
    },
    {
        "name": "iter2",
        "train_dir": PROJECT_ROOT / "data/patches_iter2/train",
        "checkpoints": [
            PROJECT_ROOT / "models/best_resnet18_patch_iter2.pt",
            PROJECT_ROOT / "models/iter2/best_resnet18_patch.pt",
        ],
    },
    {
        "name": "iter3",
        "train_dir": PROJECT_ROOT / "data/patches_iter3/train",
        "checkpoints": [
            PROJECT_ROOT / "models/best_resnet18_patch_iter3.pt",
            PROJECT_ROOT / "models/iter3/best_resnet18_patch.pt",
            # Backward-compatible name from the early single-checkpoint workflow.
            PROJECT_ROOT / "models/best_resnet18_patch.pt",
        ],
    },
]

EVAL_SPLITS = {
    "val": PROJECT_ROOT / "data/patches_base/val",
    "test": PROJECT_ROOT / "data/patches_base/test",
}

VALID_EXT = {".png", ".jpg", ".jpeg"}


def is_valid_file(path):
    p = Path(path)
    return p.suffix.lower() in VALID_EXT and not p.name.startswith("._")


def count_images(folder):
    folder = Path(folder)
    counts = Counter()

    for label in ["normal", "tumor"]:
        label_dir = folder / label
        if not label_dir.exists():
            counts[label] = 0
            continue

        counts[label] = sum(
            1
            for p in label_dir.iterdir()
            if p.is_file() and is_valid_file(p)
        )

    counts["total"] = counts["normal"] + counts["tumor"]
    return counts


def first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


def build_model(checkpoint_path, device):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def load_eval_data(eval_dir, batch_size):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    dataset = datasets.ImageFolder(
        root=str(eval_dir),
        transform=transform,
        is_valid_file=is_valid_file,
    )

    if dataset.class_to_idx.get("normal") != 0 or dataset.class_to_idx.get("tumor") != 1:
        raise ValueError(
            f"Classes inattendues dans {eval_dir}: {dataset.class_to_idx}. "
            "Attendu: normal=0, tumor=1."
        )

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    return dataset, loader


def collect_probs(model, loader, device):
    all_probs = []
    all_labels = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1]

            all_probs.extend(probs.cpu().tolist())
            all_labels.extend(labels.tolist())

    return all_probs, all_labels


def compute_metrics(labels, probs, threshold):
    preds = [1 if p > threshold else 0 for p in probs]
    cm = confusion_matrix(labels, preds, labels=[0, 1])

    tn, fp, fn, tp = cm.ravel()
    return {
        "threshold": threshold,
        "accuracy": accuracy_score(labels, preds),
        "tumor_precision": precision_score(labels, preds, pos_label=1, zero_division=0),
        "tumor_recall": recall_score(labels, preds, pos_label=1, zero_division=0),
        "tumor_f1": f1_score(labels, preds, pos_label=1, zero_division=0),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_dataset_summary(rows):
    print("\n=== Dataset summary ===")
    print("experiment,train_normal,train_tumor,train_total,checkpoint")
    for row in rows:
        print(
            f"{row['experiment']},"
            f"{row['train_normal']},"
            f"{row['train_tumor']},"
            f"{row['train_total']},"
            f"{row['checkpoint_status']}"
        )


def print_metric_summary(rows):
    print("\n=== Metrics summary ===")
    if not rows:
        print("Aucun checkpoint disponible pour evaluation.")
        return

    print("experiment,split,threshold,tumor_precision,tumor_recall,tumor_f1,fp,fn")
    for row in rows:
        print(
            f"{row['experiment']},"
            f"{row['split']},"
            f"{row['threshold']},"
            f"{row['tumor_precision']:.3f},"
            f"{row['tumor_recall']:.3f},"
            f"{row['tumor_f1']:.3f},"
            f"{row['fp']},"
            f"{row['fn']}"
        )


def resolve_device(requested):
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    return requested


def main():
    parser = argparse.ArgumentParser(
        description="Compare baseline/iter1/iter2/iter3 datasets and available checkpoints."
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs/experiment_comparison"),
        help="Directory where CSV summaries are written.",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=[0.5, 0.3, 0.2, 0.1],
        help="Tumor probability thresholds to evaluate.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Evaluation batch size.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps"],
        default="auto",
        help="Device used for model evaluation.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    device = resolve_device(args.device)
    print("device:", device)

    dataset_rows = []
    metric_rows = []

    eval_cache = {}
    for split, eval_dir in EVAL_SPLITS.items():
        if eval_dir.exists():
            eval_cache[split] = load_eval_data(eval_dir, args.batch_size)
        else:
            print(f"Eval split introuvable, skip: {eval_dir}")

    for exp in EXPERIMENTS:
        train_counts = count_images(exp["train_dir"])
        checkpoint = first_existing(exp["checkpoints"])

        dataset_rows.append({
            "experiment": exp["name"],
            "train_dir": str(exp["train_dir"]),
            "train_normal": train_counts["normal"],
            "train_tumor": train_counts["tumor"],
            "train_total": train_counts["total"],
            "checkpoint": str(checkpoint) if checkpoint else "",
            "checkpoint_status": "found" if checkpoint else "missing",
        })

        if checkpoint is None:
            print(f"[{exp['name']}] checkpoint manquant, evaluation skippee.")
            continue

        print(f"[{exp['name']}] checkpoint: {checkpoint}")
        model = build_model(checkpoint, device)

        for split, (dataset, loader) in eval_cache.items():
            probs, labels = collect_probs(model, loader, device)
            eval_counts = Counter(labels)

            for threshold in args.thresholds:
                metrics = compute_metrics(labels, probs, threshold)
                metric_rows.append({
                    "experiment": exp["name"],
                    "checkpoint": str(checkpoint),
                    "split": split,
                    "eval_dir": str(EVAL_SPLITS[split]),
                    "eval_normal": eval_counts[0],
                    "eval_tumor": eval_counts[1],
                    **metrics,
                })

    write_csv(
        output_dir / "dataset_summary.csv",
        dataset_rows,
        [
            "experiment",
            "train_dir",
            "train_normal",
            "train_tumor",
            "train_total",
            "checkpoint",
            "checkpoint_status",
        ],
    )

    write_csv(
        output_dir / "metrics.csv",
        metric_rows,
        [
            "experiment",
            "checkpoint",
            "split",
            "eval_dir",
            "eval_normal",
            "eval_tumor",
            "threshold",
            "accuracy",
            "tumor_precision",
            "tumor_recall",
            "tumor_f1",
            "tn",
            "fp",
            "fn",
            "tp",
        ],
    )

    print_dataset_summary(dataset_rows)
    print_metric_summary(metric_rows)
    print(f"\nCSV sauvegardes dans: {output_dir}")


if __name__ == "__main__":
    main()
