import torch
import random
import csv
from pathlib import Path
from collections import Counter
from PIL import Image

from torch import nn
from torch.utils.data import DataLoader, Subset, Dataset
from torchvision import transforms, models
from torchvision.datasets import ImageFolder

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
    precision_score
)

device = "cpu"
print("device:", device)

THRESHOLD = 0.2


def remove_mac_hidden_files(root_dir):
    root_dir = Path(root_dir)
    for path in root_dir.rglob("._*"):
        path.unlink(missing_ok=True)


def is_valid_file(path):
    return path.endswith(".png") and not Path(path).name.startswith("._")


class CSVPatchDataset(Dataset):
    def __init__(self, csv_file, transform=None):
        self.samples = []
        self.transform = transform
        self.classes = ["normal", "tumor"]

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.samples.append((row["path"], int(row["label"])))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")

        if self.transform:
            img = self.transform(img)

        return img, label


def main():
    # ===== CLEAN =====
    remove_mac_hidden_files("../data/patches_split")
    remove_mac_hidden_files("../data/hard_negatives")

    # ===== CREATE MODEL DIR =====
    Path("../models").mkdir(parents=True, exist_ok=True)

    # ===== TRANSFORMS =====
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

    # ===== DATA =====
    train_data_full = CSVPatchDataset(
        csv_file="../data/train_dataset.csv",
        transform=train_transform
    )

    val_data_full = ImageFolder(
        root="../data/patches_split/val",
        transform=val_transform,
        is_valid_file=is_valid_file
    )

    # ===== SUBSETS =====
    max_train_samples = 4000
    max_val_samples = 500
    random.seed(42)

    train_indices = random.sample(
        range(len(train_data_full)),
        min(len(train_data_full), max_train_samples)
    )

    val_indices = random.sample(
        range(len(val_data_full)),
        min(len(val_data_full), max_val_samples)
    )

    train_data = Subset(train_data_full, train_indices)
    val_data = Subset(val_data_full, val_indices)

    train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=32, shuffle=False)

    # ===== DISTRIBUTION CORRECTE =====
    train_labels = [train_data_full.samples[i][1] for i in train_indices]
    val_labels = [val_data_full.samples[i][1] for i in val_indices]

    print("Train distribution:", Counter(train_labels))
    print("Val distribution:", Counter(val_labels))

    # ===== MODEL =====
    model = models.resnet18(weights="IMAGENET1K_V1")
    model.fc = nn.Linear(model.fc.in_features, 2)
    model = model.to(device)

    # ===== LOSS =====
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor([1.0, 2.0], dtype=torch.float32).to(device)
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    epochs = 10
    best_val_f1 = 0.0

    for epoch in range(epochs):
        # ===== TRAIN =====
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

        # ===== VAL =====
        model.eval()
        val_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)

                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)

                probs = torch.softmax(outputs, dim=1)[:, 1]
                preds = (probs > THRESHOLD).int()

                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        # ===== METRICS =====
        tumor_f1 = f1_score(all_labels, all_preds, pos_label=1, zero_division=0)
        tumor_recall = recall_score(all_labels, all_preds, pos_label=1, zero_division=0)
        tumor_precision = precision_score(all_labels, all_preds, pos_label=1, zero_division=0)

        print(f"\nEpoch {epoch+1}/{epochs}")
        print(f"Train loss: {train_loss:.4f}")
        print(f"Tumor precision: {tumor_precision:.4f}")
        print(f"Tumor recall:    {tumor_recall:.4f}")
        print(f"Tumor f1:        {tumor_f1:.4f}")

        # ===== SAVE BEST =====
        if tumor_f1 > best_val_f1:
            best_val_f1 = tumor_f1
            torch.save(model.state_dict(), "../models/best_resnet18_patch.pt")
            print("Best model saved.")

    # ===== FINAL EVAL =====
    print("\nReload best model...")
    model.load_state_dict(torch.load("../models/best_resnet18_patch.pt", map_location=device))
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1]
            preds = (probs > THRESHOLD).int()

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    print("\nFinal confusion matrix:")
    print(confusion_matrix(all_labels, all_preds))

    print("\nFinal classification report:")
    print(classification_report(all_labels, all_preds, target_names=["normal", "tumor"]))


if __name__ == "__main__":
    main()