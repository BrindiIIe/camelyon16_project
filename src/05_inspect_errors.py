import torch
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

device = "cpu"
THRESHOLD = 0.2

# ===== OUTPUT DIR =====
Path("../errors/fn").mkdir(parents=True, exist_ok=True)
Path("../errors/fp").mkdir(parents=True, exist_ok=True)

# ===== TRANSFORM =====
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# ===== DATA =====
dataset = datasets.ImageFolder(
    root="../data/patches_split/val",
    transform=transform
)

loader = DataLoader(dataset, batch_size=1, shuffle=False)

# ===== MODEL =====
model = models.resnet18()
model.fc = torch.nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load("../models/best_resnet18_patch.pt", map_location=device))
model.to(device)
model.eval()

# ===== LOOP =====
fn_count = 0
fp_count = 0

with torch.no_grad():
    for i, (img, label) in enumerate(loader):
        img = img.to(device)
        label = label.item()

        output = model(img)
        prob = torch.softmax(output, dim=1)[0, 1].item()
        pred = int(prob > THRESHOLD)

        path, _ = dataset.samples[i]
        filename = Path(path).name

        # ===== FALSE NEGATIVE =====
        if label == 1 and pred == 0:
            fn_count += 1
            Image.open(path).save(f"../errors/fn/FN_{fn_count}_{prob:.2f}_{filename}")

        # ===== FALSE POSITIVE =====
        if label == 0 and pred == 1:
            fp_count += 1
            Image.open(path).save(f"../errors/fp/FP_{fp_count}_{prob:.2f}_{filename}")

print(f"False negatives: {fn_count}")
print(f"False positives: {fp_count}")