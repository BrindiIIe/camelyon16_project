from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from tissue_mask import make_tissue_mask
import csv
import random
import math

import openslide
from PIL import Image, ImageDraw

WSI_DIR = Path("../data/wsi")
CSV_DIR = Path("../data/inference")
OUTPUT_DIR = Path("../data/hard_negatives")
CONTACT_SHEET_DIR = OUTPUT_DIR / "contact_sheets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CONTACT_SHEET_DIR.mkdir(parents=True, exist_ok=True)

WSI_NAMES = [
   #"normal_007.tif",
    "normal_008.tif",
    "normal_009.tif",
    #"normal_010.tif",
]

LOW = 0.5
HIGH = 1
PATCH_SIZE = 256
MAX_PER_SLIDE = 50
RANDOM_SEED = 42

MIN_TISSUE_DISTANCE = 8      # distance min au bord du tissu sur thumbnail
MIN_DIST_BETWEEN = 1000      # distance min entre 2 centres en level 0
MIN_TISSUE_FRACTION = 0.40   # fraction minimale de tissu dans le patch
THUMB_SIZE = (1200, 1200)

CONTACT_PATCH_SIZE = 128
CONTACT_NCOLS = 5


def extract_patch(slide, x, y, patch_size=256, level=0):
    patch = slide.read_region(
        (x, y),
        level,
        (patch_size, patch_size)
    ).convert("RGB")
    return patch


def patch_within_bounds(slide, x, y, patch_size=256):
    half = patch_size // 2
    w, h = slide.dimensions
    return (
        x - half >= 0 and
        y - half >= 0 and
        x + half < w and
        y + half < h
    )


def tissue_fraction_rgb(patch_np, white_thresh=220):
    gray = patch_np.mean(axis=2)
    tissue = gray < white_thresh
    return tissue.mean()

def get_center(x, y, patch_size=256):
    return x + patch_size // 2, y + patch_size // 2


def is_far_enough(x, y, selected, min_dist):
    cx, cy = get_center(x, y, PATCH_SIZE)
    for s in selected:
        sx, sy = get_center(s["x"], s["y"], PATCH_SIZE)
        if (cx - sx)**2 + (cy - sy)**2 <= min_dist**2:
            return False
    return True


def make_contact_sheet(image_paths, out_path, thumb_size=128, ncols=5, title=None):
    if not image_paths:
        return

    images = []
    captions = []

    for p in image_paths:
        img = Image.open(p).convert("RGB")
        img = img.resize((thumb_size, thumb_size))
        images.append(img)
        captions.append(Path(p).stem[:40])

    n = len(images)
    nrows = math.ceil(n / ncols)

    caption_h = 20
    top_margin = 30 if title else 0

    sheet_w = ncols * thumb_size
    sheet_h = top_margin + nrows * (thumb_size + caption_h)

    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)

    if title:
        draw.text((10, 5), title, fill="black")

    for i, (img, cap) in enumerate(zip(images, captions)):
        row = i // ncols
        col = i % ncols

        x = col * thumb_size
        y = top_margin + row * (thumb_size + caption_h)

        sheet.paste(img, (x, y))
        draw.text((x + 2, y + thumb_size + 2), cap, fill="black")

    sheet.save(out_path)
    print(f"contact sheet sauvegardée: {out_path}")


def main():
    random.seed(RANDOM_SEED)

    total_saved = 0
    normal_wsi_files = []
    for name in WSI_NAMES:
        wsi_path = WSI_DIR / name
        normal_wsi_files.append(wsi_path)

    if not normal_wsi_files:
        raise FileNotFoundError(f"Aucune lame normale trouvée dans {WSI_DIR}")

    for wsi_path in normal_wsi_files:
        csv_path = CSV_DIR / f"{wsi_path.stem}_probs.csv"

        if not csv_path.exists():
            print(f"CSV manquant, skip: {csv_path}")
            continue

        print(f"\n=== {wsi_path.name} ===")

        slide = openslide.OpenSlide(str(wsi_path))
        thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
        thumb_np = np.array(thumb)

        tissue_mask, *_ = make_tissue_mask(thumb_np)
        tissue_mask = tissue_mask.astype(bool)
        dist_map = distance_transform_edt(tissue_mask)

        candidates = []

        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                x = int(float(row["x"]))
                y = int(float(row["y"]))
                prob = float(row["prob_tumor"])

                if not patch_within_bounds(slide, x, y, PATCH_SIZE):
                    continue

                tx = round(x * thumb.size[0] / slide.dimensions[0])
                ty = round(y * thumb.size[1] / slide.dimensions[1])

                if not (0 <= tx < dist_map.shape[1] and 0 <= ty < dist_map.shape[0]):
                    continue

                if not tissue_mask[ty, tx]:
                    continue

                dist = dist_map[ty, tx]

                if LOW <= prob <= HIGH and dist >= MIN_TISSUE_DISTANCE:
                    candidates.append({
                        "x": x,
                        "y": y,
                        "prob": prob,
                        "dist": dist
                    })

        print("candidats hard negatives:", len(candidates))

        if not candidates:
            slide.close()
            continue

        # on privilégie les proba les plus hautes
        candidates = sorted(
            candidates,
            key=lambda r: (-r["prob"], -r["dist"])
        )

        selected = []
        for row in candidates:
            if is_far_enough(row["x"], row["y"], selected, MIN_DIST_BETWEEN):
                selected.append(row)
            if len(selected) >= MAX_PER_SLIDE:
                break

        print("hard negatives retenus avant filtre patch:", len(selected))

        saved_here = 0
        saved_paths = []

        for i, row in enumerate(selected):
            patch = extract_patch(
                slide,
                row["x"],
                row["y"],
                patch_size=PATCH_SIZE,
                level=0
            )
            patch_np = np.array(patch)

            frac_tissue = tissue_fraction_rgb(patch_np)

            if frac_tissue < MIN_TISSUE_FRACTION:
                continue

            out_name = (
                f"{wsi_path.stem}_hardneg_"
                f"{i:03d}_"
                f"{row['x']}_{row['y']}_"
                f"{row['prob']:.3f}.png"
            )
            out_path = OUTPUT_DIR / out_name
            patch.save(out_path)

            saved_here += 1
            saved_paths.append(out_path)

        slide.close()

        total_saved += saved_here
        print("hard negatives sauvegardés:", saved_here)

        if saved_paths:
            contact_sheet_path = CONTACT_SHEET_DIR / f"{wsi_path.stem}_contact_sheet.jpg"
            make_contact_sheet(
                saved_paths,
                contact_sheet_path,
                thumb_size=CONTACT_PATCH_SIZE,
                ncols=CONTACT_NCOLS,
                title=f"{wsi_path.stem} - hard negatives"
            )

    print("\n=== RÉSUMÉ ===")
    print("total hard negatives sauvegardés:", total_saved)


if __name__ == "__main__":
    main()