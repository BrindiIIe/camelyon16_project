from tissue_utils import (
    generate_candidate_centers,
    keep_centers_in_tissue,
    extract_patch,
)
from tissue_mask import make_tissue_mask
from pathlib import Path
import csv

import torch
from torch import nn
from torchvision import transforms, models
import openslide
import numpy as np


WSI_DIR = Path("../data/wsi")
MODEL_PATH = Path("../best_resnet18_patch.pt")
OUTPUT_DIR = Path("../data/inference")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WSI_NAMES = [
    "normal_001.tif",
    "normal_002.tif",
    "normal_003.tif",
    "normal_004.tif",
    "normal_005.tif",
    "normal_006.tif",
    "normal_007.tif",
    "normal_008.tif",
    "normal_009.tif",
    "normal_010.tif",
]

PATCH_SIZE = 256
STRIDE = 256
THUMB_SIZE = (1200, 1200)
BATCH_SIZE = 64

SAVE_ONLY_ABOVE = 0.50

device = "mps" if torch.backends.mps.is_available() else "cpu"
print("device:", device)


def build_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    state_dict = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def infer_one_slide(wsi_path, model):
    output_csv = OUTPUT_DIR / f"{wsi_path.stem}_probs.csv"

    if output_csv.exists():
        print("CSV déjà présent, skip:", output_csv)
        return

    slide = openslide.OpenSlide(str(wsi_path))

    thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
    thumb_np = np.array(thumb)
    tissue_mask = make_tissue_mask(thumb_np)

    candidate_centers = generate_candidate_centers(
        slide_dims=slide.dimensions,
        patch_size=PATCH_SIZE,
        stride=STRIDE
    )

    kept_centers = keep_centers_in_tissue(
        candidate_centers,
        tissue_mask,
        full_size=slide.dimensions,
        thumb_size=thumb.size
    )

    print(f"\nslide: {wsi_path.name}")
    print("total candidats:", len(candidate_centers))
    print("dans le tissu:", len(kept_centers))

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    results = []

    with torch.no_grad():
        for i in range(0, len(kept_centers), BATCH_SIZE):
            batch_centers = kept_centers[i:i + BATCH_SIZE]

            images = []
            valid_centers = []

            for x, y in batch_centers:
                try:
                    patch = extract_patch(slide, x, y, patch_size=PATCH_SIZE, level=0)
                    images.append(transform(patch))
                    valid_centers.append((x, y))
                except Exception as e:
                    print(f"patch skip ({x}, {y}): {e}")

            if not images:
                continue

            images = torch.stack(images).to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()

            for (x, y), p in zip(valid_centers, probs):
                if p >= SAVE_ONLY_ABOVE:
                    results.append((x, y, float(p)))

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "prob_tumor"])
        writer.writerows(results)

    slide.close()
    print("CSV sauvegardé:", output_csv)
    print("nb résultats sauvegardés:", len(results))


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modèle introuvable: {MODEL_PATH}")

    model = build_model()

    for name in WSI_NAMES:
        wsi_path = WSI_DIR / name
        if not wsi_path.exists():
            print("WSI introuvable, skip:", wsi_path)
            continue
        infer_one_slide(wsi_path, model)


if __name__ == "__main__":
    main()