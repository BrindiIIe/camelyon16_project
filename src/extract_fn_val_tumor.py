import shutil
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms, models
from torchvision.datasets import ImageFolder


device = "mps" if torch.backends.mps.is_available() else "cpu"
print("device:", device)

VAL_DIR = "../data/patches_base/val"
MODEL_PATH = "../models/best_resnet18_patch.pt"
OUTPUT_DIR = Path("../data/review/false_negatives_val_tumor")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_valid_file(path):
    return path.endswith(".png") and not Path(path).name.startswith("._")


def build_model(num_classes=2):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def main():
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    val_data = ImageFolder(
        root=VAL_DIR,
        transform=transform,
        is_valid_file=is_valid_file
    )

    val_loader = DataLoader(
        val_data,
        batch_size=16,
        shuffle=False
    )

    class_to_idx = val_data.class_to_idx

    if "tumor" not in class_to_idx or "normal" not in class_to_idx:
        raise ValueError("Classes attendues: normal / tumor")

    tumor_idx = class_to_idx["tumor"]
    normal_idx = class_to_idx["normal"]

    model = build_model(num_classes=len(class_to_idx))
    state_dict = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    all_preds = []

    with torch.no_grad():
        for images, _ in val_loader:
            images = images.to(device)
            logits = model(images)
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().tolist())

    fn_count = 0

    for idx, ((path, true_label), pred_label) in enumerate(zip(val_data.samples, all_preds)):
        if true_label == tumor_idx and pred_label == normal_idx:
            src = Path(path)
            dst = OUTPUT_DIR / src.name

            if dst.exists():
                stem = src.stem
                suffix = src.suffix
                i = 1
                while True:
                    candidate = OUTPUT_DIR / f"{stem}_{i}{suffix}"
                    if not candidate.exists():
                        dst = candidate
                        break
                    i += 1

            shutil.copy(src, dst)
            fn_count += 1

    print(f"Faux négatifs tumor extraits : {fn_count}")
    print(f"Dossier : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
