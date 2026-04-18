import torch
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

device = "mps" if torch.backends.mps.is_available() else "cpu"

# ===== DATA =====
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

val_data = datasets.ImageFolder(
    root="../data/patches_split/val",
    transform=transform
)

val_loader = DataLoader(val_data, batch_size=16, shuffle=False)

# ===== MODEL =====
model = models.resnet18()
model.fc = torch.nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load("../models/best_resnet18_patch.pt", map_location=device))
model.to(device)
model.eval()

# ===== INFERENCE =====
all_probs = []
all_labels = []

with torch.no_grad():
    for images, labels in val_loader:
        images = images.to(device)
        labels = labels.to(device)

        outputs = model(images)
        probs = torch.softmax(outputs, dim=1)[:, 1]

        all_probs.extend(probs.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

all_probs = torch.tensor(all_probs)
all_labels = torch.tensor(all_labels)

# ===== TEST SEUILS =====
thresholds = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1]

for th in thresholds:
    preds = (all_probs > th).long()

    cm = confusion_matrix(all_labels.numpy(), preds.numpy())
    precision = precision_score(all_labels.numpy(), preds.numpy(), pos_label=1, zero_division=0)
    recall = recall_score(all_labels.numpy(), preds.numpy(), pos_label=1, zero_division=0)
    f1 = f1_score(all_labels.numpy(), preds.numpy(), pos_label=1, zero_division=0)

    print(f"\nThreshold = {th}")
    print(cm)
    print(f"tumor precision = {precision:.3f}")
    print(f"tumor recall    = {recall:.3f}")
    print(f"tumor f1        = {f1:.3f}")