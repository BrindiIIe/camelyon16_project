from pathlib import Path
from matplotlib.patches import Polygon
import csv
import xml.etree.ElementTree as ET
import openslide
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter


# =========================
# CONFIG
# =========================
XML_DIR = Path("../data/annotations")
WSI_DIR = Path("../data/wsi")
CSV_DIR = Path("../data/inference")
OUTPUT_DIR = Path("../data/inference/heatmaps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
 # change ici
WSI_NAMES = [
    WSI_DIR / "tumor_006.tif",
    WSI_DIR / "tumor_007.tif",
    WSI_DIR / "normal_008.tif",
    WSI_DIR / "normal_009.tif",
]
THUMB_SIZE = (1200, 1200)
PATCH_SIZE = 256

# OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)

def parse_polygons_from_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    polygons = []
    for annotation in root.iter("Annotation"):
        coords = annotation.find("Coordinates")
        if coords is None:
            continue

        poly = []
        for coord in coords.findall("Coordinate"):
            x = float(coord.attrib["X"])
            y = float(coord.attrib["Y"])
            poly.append((x, y))

        if len(poly) >= 3:
            polygons.append(poly)

    return polygons

def level0_to_thumbnail_coords(x, y, full_size, thumb_size):
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    tx = int(x * thumb_w / full_w)
    ty = int(y * thumb_h / full_h)
    return tx, ty

def level0_to_thumbnail_coords_float(x, y, full_size, thumb_size):
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    tx = x * thumb_w / full_w
    ty = y * thumb_h / full_h
    return tx, ty


def visualize_one(wsi_path, csv_path, output_fig):
    if not wsi_path.exists():
        raise FileNotFoundError(f"WSI introuvable: {wsi_path}")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV introuvable: {csv_path}")

    slide = openslide.OpenSlide(str(wsi_path))
    thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
    thumb_np = np.array(thumb)
    xml_path = XML_DIR / f"{wsi_path.stem}.xml"

    xs_thumb = []
    ys_thumb = []
    probs = []

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            x = int(float(row["x"]))
            y = int(float(row["y"]))
            p = float(row["prob_tumor"])

            tx, ty = level0_to_thumbnail_coords(x, y, slide.dimensions, thumb.size)

            xs_thumb.append(tx)
            ys_thumb.append(ty)
            probs.append(p)

    thumb_w, thumb_h = thumb.size

    heatmap = np.zeros((thumb_h, thumb_w), dtype=float)
    counts = np.zeros((thumb_h, thumb_w), dtype=float)

    patch_w_thumb = max(3, int(np.ceil(PATCH_SIZE * thumb_w / slide.dimensions[0])))
    patch_h_thumb = max(3, int(np.ceil(PATCH_SIZE * thumb_h / slide.dimensions[1])))

    half_w = patch_w_thumb // 2
    half_h = patch_h_thumb // 2

    for tx, ty, p in zip(xs_thumb, ys_thumb, probs):
        x0 = max(0, tx - half_w)
        x1 = min(thumb_w, tx + half_w + 1)
        y0 = max(0, ty - half_h)
        y1 = min(thumb_h, ty + half_h + 1)

        heatmap[y0:y1, x0:x1] += p
        counts[y0:y1, x0:x1] += 1

    heatmap = np.divide(
        heatmap,
        counts,
        out=np.zeros_like(heatmap),
        where=counts > 0
    )

    raw_vals = heatmap[counts > 0]

    if raw_vals.size > 0:
        print("raw min:", np.min(raw_vals))
        print("raw max:", np.max(raw_vals))
        print("raw mean:", np.mean(raw_vals))
        print("raw p95:", np.percentile(raw_vals, 95))
        print("raw p99:", np.percentile(raw_vals, 99))

    heatmap[counts == 0] = np.nan

    # Ne pas masquer au seuil fixe pour l’instant
    # heatmap[heatmap < 0.1] = np.nan

    heatmap_for_filter = np.nan_to_num(heatmap, nan=0.0)
    heatmap = gaussian_filter(heatmap_for_filter, sigma=2)
    heatmap[counts == 0] = np.nan
    valid_vals = heatmap[~np.isnan(heatmap)]

    print("nb pixels couverts:", np.sum(~np.isnan(heatmap)))

    if valid_vals.size > 0:
        print("min:", np.min(valid_vals))
        print("max:", np.max(valid_vals))
        print("mean:", np.mean(valid_vals))
    else:
        print("Heatmap vide : aucune valeur non-NaN")
        print("nb pixels couverts:", np.sum(~np.isnan(heatmap)))

    plt.figure(figsize=(10, 10))
    plt.imshow(thumb_np)
    valid_vals = heatmap[~np.isnan(heatmap)]

    if valid_vals.size > 0:
        vmin = np.nanpercentile(valid_vals, 10)
        vmax = np.nanpercentile(valid_vals, 99)
    else:
        vmin, vmax = 0.0, 1.0

    im = plt.imshow(
        heatmap,
        cmap="hot",
        alpha=0.75,
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar(im, label="Probabilité tumorale")
    plt.title(f"Heatmap tumorale - {wsi_path.name}")
    plt.axis("off")

    ax = plt.gca()

    if xml_path.exists():
        polygons = parse_polygons_from_xml(xml_path)
        print("nb polygons:", len(polygons))

        for poly in polygons:
            thumb_poly = [
                level0_to_thumbnail_coords_float(x, y, slide.dimensions, thumb.size)
                for x, y in poly
            ]

            patch = Polygon(
                thumb_poly,
                closed=True,
                fill=False,
                edgecolor="lime",
                linewidth=2
            )
            ax.add_patch(patch)
    plt.tight_layout()
    plt.savefig(output_fig, dpi=200, bbox_inches="tight")
    plt.show()
    slide.close()
    print("Heatmap sauvegardée:", output_fig)

def main():
    for wsi_path in WSI_NAMES:
        wsi_path = Path(wsi_path)
        csv_path = CSV_DIR / f"{wsi_path.stem}_probs.csv"
        output_fig = OUTPUT_DIR / f"{wsi_path.stem}_heatmap.png"

        if not csv_path.exists():
            print("CSV manquant, skip:", csv_path)
            continue

        print("\nTraitement:", wsi_path.name)

        visualize_one(wsi_path, csv_path, output_fig)
        
        print("→ saved:", output_fig)

if __name__ == "__main__":
    main()