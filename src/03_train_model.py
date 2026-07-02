import torch
import random
import argparse
from pathlib import Path
from collections import Counter

from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import transforms, models
from torchvision.datasets import ImageFolder

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
    precision_score
)

THRESHOLD = 0.2

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPERIMENTS = {
    "baseline": {
        "train_dir": PROJECT_ROOT / "data/patches_base/train",
        "model_path": PROJECT_ROOT / "models/best_resnet18_patch_baseline.pt",
    },
    "iter1": {
        "train_dir": PROJECT_ROOT / "data/patches_iter1/train",
        "model_path": PROJECT_ROOT / "models/best_resnet18_patch_iter1.pt",
    },
    "iter2": {
        "train_dir": PROJECT_ROOT / "data/patches_iter2/train",
        "model_path": PROJECT_ROOT / "models/best_resnet18_patch_iter2.pt",
    },
    "iter3": {
        "train_dir": PROJECT_ROOT / "data/patches_iter3/train",
        "model_path": PROJECT_ROOT / "models/best_resnet18_patch_iter3.pt",
    },
    "iter4": {
        "train_dir": PROJECT_ROOT / "data/patches_iter4/train",
        "model_path": PROJECT_ROOT / "models/best_resnet18_patch_iter4.pt",
    },
}

VAL_DIR = PROJECT_ROOT / "data/patches_base/val"


def remove_mac_hidden_files(root_dir):
    root_dir = Path(root_dir)
    for path in root_dir.rglob("._*"):
        path.unlink(missing_ok=True)


def is_valid_file(path):
    return path.endswith(".png") and not Path(path).name.startswith("._")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train ResNet18 patch classifier for one experiment."
    )
    parser.add_argument(
        "--experiment",
        choices=sorted(EXPERIMENTS.keys()),
        default="iter3",
        help="Training dataset/checkpoint pair to use.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=THRESHOLD,
        help="Tumor probability threshold used during validation.",
    )
    parser.add_argument(
        "--max-train-samples",
        type=int,
        default=4000,
        help="Maximum number of training patches sampled per run.",
    )
    parser.add_argument(
        "--max-val-samples",
        type=int,
        default=500,
        help="Maximum number of validation patches sampled per run.",
    )
    parser.add_argument(
        "--also-update-latest",
        action="store_true",
        help="Also copy the best checkpoint to models/best_resnet18_patch.pt.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps"],
        default="auto",
        help="Device used for training.",
    )
    return parser.parse_args()


def resolve_device(requested):
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    return requested


def main():
    args = parse_args()
    device = resolve_device(args.device)
    experiment = EXPERIMENTS[args.experiment]
    train_dir = experiment["train_dir"]
    model_path = experiment["model_path"]
    latest_model_path = PROJECT_ROOT / "models/best_resnet18_patch.pt"

    if not train_dir.exists():
        raise FileNotFoundError(f"Train dir introuvable: {train_dir}")
    if not VAL_DIR.exists():
        raise FileNotFoundError(f"Val dir introuvable: {VAL_DIR}")

    print("device:", device, flush=True)
    print("experiment:", args.experiment, flush=True)
    print("train_dir:", train_dir, flush=True)
    print("val_dir:", VAL_DIR, flush=True)
    print("model_path:", model_path, flush=True)

    remove_mac_hidden_files(train_dir)
    Path(PROJECT_ROOT / "models").mkdir(parents=True, exist_ok=True)

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomApply([
            transforms.ColorJitter(brightness=0.2, contrast=0.2)
        ], p=0.5),
        transforms.ToTensor(),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    train_data_full = ImageFolder(
        root=str(train_dir),
        transform=train_transform,
        is_valid_file=is_valid_file
    )

    val_data_full = ImageFolder(
        root=str(VAL_DIR),
        transform=val_transform,
        is_valid_file=is_valid_file
    )

    print("Train classes:", train_data_full.class_to_idx, flush=True)
    print("Val classes:", val_data_full.class_to_idx, flush=True)

    random.seed(42)

    train_indices = random.sample(
        range(len(train_data_full)),
        min(len(train_data_full), args.max_train_samples)
    )

    val_indices = random.sample(
        range(len(val_data_full)),
        min(len(val_data_full), args.max_val_samples)
    )

    train_data = Subset(train_data_full, train_indices)
    val_data = Subset(val_data_full, val_indices)

    train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=32, shuffle=False)

    train_labels = [train_data_full.samples[i][1] for i in train_indices]
    val_labels = [val_data_full.samples[i][1] for i in val_indices]

    print("Train distribution:", Counter(train_labels), flush=True)
    print("Val distribution:", Counter(val_labels), flush=True)

    model = models.resnet18(weights="IMAGENET1K_V1")
    model.fc = nn.Linear(model.fc.in_features, 2)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor([1.0, 2.0], dtype=torch.float32).to(device)
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    best_val_f1 = 0.0

    for epoch in range(args.epochs):
        model.train()
        train_loss = 0.0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)

        model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)

                outputs = model(images)
                probs = torch.softmax(outputs, dim=1)[:, 1]
                preds = (probs > args.threshold).int()

                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        tumor_f1 = f1_score(all_labels, all_preds, pos_label=1, zero_division=0)
        tumor_recall = recall_score(all_labels, all_preds, pos_label=1, zero_division=0)
        tumor_precision = precision_score(all_labels, all_preds, pos_label=1, zero_division=0)

        avg_train_loss = train_loss / len(train_data)

        print(f"\nEpoch {epoch+1}/{args.epochs}", flush=True)
        print(f"Train loss: {avg_train_loss:.4f}", flush=True)
        print(f"Tumor precision: {tumor_precision:.4f}", flush=True)
        print(f"Tumor recall:    {tumor_recall:.4f}", flush=True)
        print(f"Tumor f1:        {tumor_f1:.4f}", flush=True)

        if tumor_f1 > best_val_f1:
            best_val_f1 = tumor_f1
            torch.save(model.state_dict(), model_path)
            print("Best model saved.", flush=True)

    print("\nReload best model...", flush=True)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1]
            preds = (probs > args.threshold).int()

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    print("\nFinal confusion matrix:", flush=True)
    print(confusion_matrix(all_labels, all_preds), flush=True)

    print("\nFinal classification report:", flush=True)
    print(classification_report(all_labels, all_preds, target_names=["normal", "tumor"]), flush=True)

    if args.also_update_latest:
        torch.save(model.state_dict(), latest_model_path)
        print("Latest model updated:", latest_model_path, flush=True)


if __name__ == "__main__":
    main()
