from pathlib import Path
import argparse
import csv
from collections import defaultdict

import torch
from torch import nn
from torchvision import models, transforms
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_CSV = PROJECT_ROOT / "outputs/micro_fp_review_iter2/review_template.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/micro_fp_iter2_vs_iter4"

CHECKPOINTS = {
    "iter2": PROJECT_ROOT / "models/best_resnet18_patch_iter2.pt",
    "iter4": PROJECT_ROOT / "models/best_resnet18_patch_iter4.pt",
}


def is_patch_file(path):
    path = Path(path)
    return (
        path.is_file()
        and path.suffix.lower() == ".png"
        and not path.name.startswith("._")
        and "contact_sheet" not in path.name
        and "overview" not in path.name
    )


def build_model(checkpoint_path, device):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def collect_review_patches(review_csv, include_decisions):
    patches = []
    with open(review_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = row["include_as_hard_negative"].strip().lower()
            if decision not in include_decisions:
                continue

            patch_dir = Path(row["contact_sheet"]).parent
            for patch_path in sorted(p for p in patch_dir.iterdir() if is_patch_file(p)):
                patches.append({
                    "slide_id": row["slide_id"],
                    "component_id": row["component_id"],
                    "decision": decision,
                    "review_category": row["review_category"],
                    "notes": row["notes"],
                    "patch_path": patch_path,
                })
    return patches


def predict_probs(model, patches, device, batch_size):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    probs = []

    with torch.no_grad():
        for i in range(0, len(patches), batch_size):
            batch = patches[i:i + batch_size]
            images = [
                transform(Image.open(item["patch_path"]).convert("RGB"))
                for item in batch
            ]
            tensor = torch.stack(images).to(device)
            outputs = model(tensor)
            batch_probs = torch.softmax(outputs, dim=1)[:, 1].cpu().tolist()
            probs.extend(batch_probs)

    return probs


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row["slide_id"], row["component_id"], row["decision"], row["review_category"])
        grouped[key].append(row)

    lines = [
        "# Micro False-Positive Patch Probabilities: Iter2 vs Iter4",
        "",
        "This compares the already extracted iter2 micro false-positive review patches.",
        "It does not replace full WSI inference, but it tests whether iter4 learned to downscore the reviewed hard negatives.",
        "",
        "| Slide | Component | Decision | Category | N | Mean iter2 | Mean iter4 | Delta | Iter2 >= 0.99 | Iter4 >= 0.99 |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for key, values in sorted(grouped.items()):
        slide_id, component_id, decision, category = key
        mean_iter2 = sum(v["prob_iter2"] for v in values) / len(values)
        mean_iter4 = sum(v["prob_iter4"] for v in values) / len(values)
        iter2_high = sum(v["prob_iter2"] >= 0.99 for v in values)
        iter4_high = sum(v["prob_iter4"] >= 0.99 for v in values)
        lines.append(
            f"| {slide_id} | {component_id} | {decision} | {category} | "
            f"{len(values)} | {mean_iter2:.3f} | {mean_iter4:.3f} | "
            f"{(mean_iter4 - mean_iter2):.3f} | {iter2_high} | {iter4_high} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare iter2/iter4 probabilities on extracted micro false-positive review patches."
    )
    parser.add_argument("--review-csv", default=str(REVIEW_CSV))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--device", choices=["cpu", "mps"], default="cpu")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--include-decisions",
        nargs="+",
        default=["yes", "maybe", "no"],
        help="Review decisions to include.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    review_csv = Path(args.review_csv)
    output_dir = Path(args.output_dir)
    device = args.device

    patches = collect_review_patches(
        review_csv,
        {decision.lower() for decision in args.include_decisions},
    )
    if not patches:
        raise RuntimeError("Aucun patch trouve pour la comparaison.")

    models_by_name = {
        name: build_model(path, device)
        for name, path in CHECKPOINTS.items()
    }

    probs_by_name = {
        name: predict_probs(model, patches, device, args.batch_size)
        for name, model in models_by_name.items()
    }

    rows = []
    for idx, item in enumerate(patches):
        prob_iter2 = probs_by_name["iter2"][idx]
        prob_iter4 = probs_by_name["iter4"][idx]
        rows.append({
            "slide_id": item["slide_id"],
            "component_id": item["component_id"],
            "decision": item["decision"],
            "review_category": item["review_category"],
            "patch_path": str(item["patch_path"]),
            "prob_iter2": prob_iter2,
            "prob_iter4": prob_iter4,
            "delta_iter4_minus_iter2": prob_iter4 - prob_iter2,
            "notes": item["notes"],
        })

    write_csv(
        output_dir / "patch_probs.csv",
        rows,
        [
            "slide_id",
            "component_id",
            "decision",
            "review_category",
            "patch_path",
            "prob_iter2",
            "prob_iter4",
            "delta_iter4_minus_iter2",
            "notes",
        ],
    )
    write_summary(output_dir / "summary.md", rows)

    print("Patches compares:", len(rows))
    print("CSV:", output_dir / "patch_probs.csv")
    print("Summary:", output_dir / "summary.md")


if __name__ == "__main__":
    main()
