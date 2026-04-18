from tissue_utils import (
    make_tissue_mask,
    generate_candidate_centers,
    keep_centers_in_tissue,
    extract_patch,
    level0_to_thumbnail_coords,
)
from pathlib import Path
import csv

import torch
from torch import nn
from torchvision import transforms, models
from PIL import Image
import openslide
import numpy as np

from skimage.color import rgb2gray
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import (
    remove_small_objects,
    binary_closing,
    binary_opening,
    binary_dilation,
    binary_erosion,
    disk,
)
from scipy.ndimage import binary_fill_holes


# =========================
# CONFIG
# =========================
WSI_DIR = Path("../data/wsi")   # à changer
MODEL_PATH = Path("../models/best_resnet18_patch.pt")
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
STRIDE = 128
THUMB_SIZE = (1200, 1200)
BATCH_SIZE = 32

device = "cpu"
print("device:", device)

# OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)


# =========================
# MASK
# =========================
def keep_largest_components(mask, n=3):
    labeled = label(mask)
    regions = regionprops(labeled)

    if len(regions) == 0:
        return mask

    regions = sorted(regions, key=lambda r: r.area, reverse=True)
    keep_labels = [r.label for r in regions[:n]]
    return np.isin(labeled, keep_labels)


def clear_border_margin(mask, margin=25):
    cleaned = mask.copy()
    cleaned[:margin, :] = False
    cleaned[-margin:, :] = False
    cleaned[:, :margin] = False
    cleaned[:, -margin:] = False
    return cleaned
# =========================
# MODEL
# =========================
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

    slide = openslide.OpenSlide(str(wsi_path))

    thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
    thumb_np = np.array(thumb)
    tissue_mask, *_ = make_tissue_mask(thumb_np)
    tissue_mask = tissue_mask.astype(bool)

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
            for x, y in batch_centers:
                patch = extract_patch(slide, x, y, patch_size=PATCH_SIZE, level=0)
                images.append(transform(patch))

            images = torch.stack(images).to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()

            for (x, y), p in zip(batch_centers, probs):
                results.append((x, y, float(p)))

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "prob_tumor"])
        writer.writerows(results)

    slide.close()
    print("CSV sauvegardé:", output_csv)

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