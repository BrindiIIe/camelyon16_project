from pathlib import Path
import csv

import openslide
import matplotlib.pyplot as plt


WSI_PATH = Path("../data/wsi/normal_002.tif")   # change ici
CSV_PATH = Path("../data/inference/normal_002_probs.csv")
PATCH_SIZE = 256
TOP_K = 12


def extract_patch(slide, center_x, center_y, patch_size=256, level=0):
    half = patch_size // 2
    top_left_x = center_x - half
    top_left_y = center_y - half

    patch = slide.read_region(
        (top_left_x, top_left_y),
        level,
        (patch_size, patch_size)
    ).convert("RGB")

    return patch


def main():
    if not WSI_PATH.exists():
        raise FileNotFoundError(f"WSI introuvable: {WSI_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV introuvable: {CSV_PATH}")

    rows = []
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "x": int(float(row["x"])),
                "y": int(float(row["y"])),
                "prob": float(row["prob_tumor"]),
            })

    rows = sorted(rows, key=lambda r: r["prob"], reverse=True)[:TOP_K]

    slide = openslide.OpenSlide(str(WSI_PATH))

    plt.figure(figsize=(12, 10))
    for i, row in enumerate(rows, 1):
        patch = extract_patch(
            slide,
            row["x"],
            row["y"],
            patch_size=PATCH_SIZE,
            level=0
        )

        plt.subplot(3, 4, i)
        plt.imshow(patch)
        plt.title(f"p={row['prob']:.3f}")
        plt.axis("off")

    plt.suptitle(f"Top {TOP_K} patches - {WSI_PATH.name}")
    plt.tight_layout()
    plt.show()

    slide.close()


if __name__ == "__main__":
    main()