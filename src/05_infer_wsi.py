from tissue_utils import (
    make_tissue_mask,
    generate_candidate_centers,
    keep_centers_in_tissue,
    extract_patch,
    level0_to_thumbnail_coords,
)
from pathlib import Path
import argparse
import csv

import torch
from torch import nn
from torchvision import transforms, models
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
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WSI_DIR = PROJECT_ROOT / "data/wsi"
MODEL_PATH = PROJECT_ROOT / "models/best_resnet18_patch_iter2.pt"
OUTPUT_DIR = PROJECT_ROOT / "data/inference_iter2"

DEFAULT_WSI_NAMES = [
    *[f"tumor_{i:03d}.tif" for i in range(1, 11)],
    *[f"normal_{i:03d}.tif" for i in range(1, 11)],
]

PATCH_SIZE = 256
STRIDE = 128
THUMB_SIZE = (1200, 1200)
BATCH_SIZE = 32

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
def resolve_device(requested):
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    return requested


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run patch-level inference on WSI files and write probability CSVs."
    )
    parser.add_argument(
        "--model-path",
        default=str(MODEL_PATH),
        help="Checkpoint to use. Defaults to the iter2 checkpoint.",
    )
    parser.add_argument(
        "--wsi-dir",
        default=str(WSI_DIR),
        help="Directory containing WSI .tif files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory where *_probs.csv files are written.",
    )
    parser.add_argument(
        "--slides",
        nargs="+",
        default=DEFAULT_WSI_NAMES,
        help="WSI filenames to process.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=STRIDE,
        help="Stride in level-0 pixels.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Batch size for patch inference.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps"],
        default="auto",
        help="Device used for inference.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute CSVs even when they already exist.",
    )
    return parser.parse_args()


def build_model(model_path, device):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model

def infer_one_slide(
    wsi_path,
    model,
    output_dir,
    device,
    stride=STRIDE,
    batch_size=BATCH_SIZE,
    overwrite=False,
):
    output_csv = output_dir / f"{wsi_path.stem}_probs.csv"

    if output_csv.exists() and not overwrite:
        print("CSV deja present, skip:", output_csv, flush=True)
        return

    slide = openslide.OpenSlide(str(wsi_path))

    thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
    thumb_np = np.array(thumb)
    tissue_mask, *_ = make_tissue_mask(thumb_np)
    tissue_mask = tissue_mask.astype(bool)

    candidate_centers = generate_candidate_centers(
        slide_dims=slide.dimensions,
        patch_size=PATCH_SIZE,
        stride=stride
    )

    kept_centers = keep_centers_in_tissue(
        candidate_centers,
        tissue_mask,
        full_size=slide.dimensions,
        thumb_size=thumb.size
    )

    print(f"\nslide: {wsi_path.name}")
    print("total candidats:", len(candidate_centers))
    print("dans le tissu:", len(kept_centers), flush=True)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    results = []

    with torch.no_grad():
        for i in range(0, len(kept_centers), batch_size):
            batch_centers = kept_centers[i:i + batch_size]

            images = []
            for x, y in batch_centers:
                patch = extract_patch(slide, x, y, patch_size=PATCH_SIZE, level=0)
                images.append(transform(patch))

            if not images:
                continue

            images = torch.stack(images).to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()

            for (x, y), p in zip(batch_centers, probs):
                results.append((x, y, float(p)))

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "prob_tumor"])
        writer.writerows(results)

    slide.close()
    print("CSV sauvegarde:", output_csv, flush=True)

def main():
    args = parse_args()

    device = resolve_device(args.device)
    model_path = Path(args.model_path)
    wsi_dir = Path(args.wsi_dir)
    output_dir = Path(args.output_dir)

    print("device:", device, flush=True)
    print("model_path:", model_path, flush=True)
    print("wsi_dir:", wsi_dir, flush=True)
    print("output_dir:", output_dir, flush=True)
    print("slides:", len(args.slides), flush=True)

    if not model_path.exists():
        raise FileNotFoundError(f"Modele introuvable: {model_path}")

    model = build_model(model_path, device)

    for name in args.slides:
        wsi_path = wsi_dir / name
        if not wsi_path.exists():
            print("WSI introuvable, skip:", wsi_path)
            continue
        infer_one_slide(
            wsi_path,
            model,
            output_dir,
            device,
            stride=args.stride,
            batch_size=args.batch_size,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
