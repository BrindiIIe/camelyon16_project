from pathlib import Path
import random
import xml.etree.ElementTree as ET
from tissue_mask import make_tissue_mask
from scipy.ndimage import distance_transform_edt

from PIL import Image
import openslide
import numpy as np
import shutil

from matplotlib.path import Path as MplPath
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
WSI_DIR = Path("../data/wsi")
ANNOTATIONS_DIR = Path("../data/annotations")
OUTPUT_TUMOR = Path("../data/patches/train/tumor")
OUTPUT_NORMAL = Path("../data/patches/train/normal")
# nettoyage du dataset précédent
shutil.rmtree("../data/patches", ignore_errors=True)

OUTPUT_TUMOR.mkdir(parents=True, exist_ok=True)
OUTPUT_NORMAL.mkdir(parents=True, exist_ok=True)

PATCH_SIZE = 256
STRIDE = 256

MAX_TUMOR_SLIDES = 10
MAX_NORMAL_SLIDES = 10

MAX_NORMAL_PER_NORMAL_SLIDE = 200
MAX_TUMOR_PER_TUMOR_SLIDE = None   # ex: 500
BALANCE_NORMAL_TO_TUMOR = True

WHITE_THRESHOLD = 220
MIN_TISSUE_RATIO = 0.50


# =========================
# UTILS
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


def level0_to_thumbnail_coords(x, y, full_size, thumb_size):
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    tx = int(x * thumb_w / full_w)
    ty = int(y * thumb_h / full_h)
    return tx, ty


def is_hidden_mac_file(path: Path):
    return path.name.startswith("._")


# =========================
# GRID / PATCHES
# =========================
def get_patch_tissue_ratio(x, y, patch_size, tissue_mask, full_size, thumb_size):
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    patch_w_thumb = max(1, int(np.ceil(patch_size * thumb_w / full_w)))
    patch_h_thumb = max(1, int(np.ceil(patch_size * thumb_h / full_h)))

    tx, ty = level0_to_thumbnail_coords(x, y, full_size, thumb_size)

    half_w = patch_w_thumb // 2
    half_h = patch_h_thumb // 2

    x0 = max(0, tx - half_w)
    x1 = min(thumb_w, tx + half_w + 1)
    y0 = max(0, ty - half_h)
    y1 = min(thumb_h, ty + half_h + 1)

    patch_mask = tissue_mask[y0:y1, x0:x1]

    if patch_mask.size == 0:
        return 0.0

    return patch_mask.mean()

def keep_centers_far_from_tissue_edge(
    centers,
    tissue_mask,
    full_size,
    thumb_size,
    min_tissue_ratio=0.6,
    min_edge_distance_thumb=2,
    patch_size=256,
):
    kept = []

    h_mask, w_mask = tissue_mask.shape
    dist_map = distance_transform_edt(tissue_mask)

    for x, y in centers:
        tx, ty = level0_to_thumbnail_coords(x, y, full_size, thumb_size)

        if not (0 <= tx < w_mask and 0 <= ty < h_mask):
            continue

        if not tissue_mask[ty, tx]:
            continue

        tissue_ratio = get_patch_tissue_ratio(
            x, y,
            patch_size=patch_size,
            tissue_mask=tissue_mask,
            full_size=full_size,
            thumb_size=thumb_size
        )

        if tissue_ratio < min_tissue_ratio:
            continue

        if dist_map[ty, tx] < min_edge_distance_thumb:
            continue

        kept.append((x, y))

    return kept

def generate_candidate_centers(slide_dims, patch_size=256, stride=128):
    full_w, full_h = slide_dims
    half = patch_size // 2

    centers = []
    for y in range(half, full_h - half, stride):
        for x in range(half, full_w - half, stride):
            centers.append((x, y))

    return centers


def keep_centers_in_tissue(centers, tissue_mask, full_size, thumb_size, patch_size=256, min_tissue_ratio=0.6):
    kept = []

    h_mask, w_mask = tissue_mask.shape

    for x, y in centers:
        tx, ty = level0_to_thumbnail_coords(x, y, full_size, thumb_size)

        if not (0 <= tx < w_mask and 0 <= ty < h_mask):
            continue

        if not tissue_mask[ty, tx]:
            continue

        tissue_ratio = get_patch_tissue_ratio(
            x, y,
            patch_size=patch_size,
            tissue_mask=tissue_mask,
            full_size=full_size,
            thumb_size=thumb_size
        )

        if tissue_ratio >= min_tissue_ratio:
            kept.append((x, y))

    return kept

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


def is_informative_patch(patch, white_threshold=220, min_tissue_ratio=0.5):
    gray = np.mean(patch, axis=2)
    non_white = gray < white_threshold
    return non_white.mean() >= min_tissue_ratio


def save_patch(patch, label, slide_name, cx, cy):
    if label == "tumor":
        output_dir = OUTPUT_TUMOR
        prefix = "tumor"
    else:
        output_dir = OUTPUT_NORMAL
        prefix = "normal"

    filename = f"{slide_name}_{prefix}_{cx}_{cy}.png"
    out_path = output_dir / filename
    patch.save(out_path)
    return out_path


# =========================
# XML / ANNOTATIONS
# =========================
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
            if "X" not in coord.attrib or "Y" not in coord.attrib:
                continue

            x = float(coord.attrib["X"])
            y = float(coord.attrib["Y"])
            poly.append((x, y))

        if len(poly) >= 3:
            polygons.append(poly)

    return polygons


def build_polygon_paths(polygons):
    return [MplPath(poly) for poly in polygons]


def point_in_any_polygon(x, y, polygon_paths):
    for path in polygon_paths:
        if path.contains_point((x, y)):
            return True
    return False

def point_near_tumor(x, y, polygon_paths, margin=300):
    for path in polygon_paths:
        if path.contains_point((x, y)):
            return True
        if path.contains_point((x + margin, y)) or \
           path.contains_point((x - margin, y)) or \
           path.contains_point((x, y + margin)) or \
           path.contains_point((x, y - margin)):
            return True
    return False

# =========================
# MAIN PROCESSING
# =========================
def process_slide(
    wsi_path,
    xml_path=None,
    patch_size=256,
    stride=256,
    max_normal_per_slide=None,
    max_tumor_per_slide=None,
    balance_normal_to_tumor=True,
):
    print(f"\n--- Traitement de {wsi_path.name} ---")

    slide = openslide.OpenSlide(str(wsi_path))

    thumb = slide.get_thumbnail((1200, 1200)).convert("RGB")
    thumb_np = np.array(thumb)
    tissue_mask, *_ = make_tissue_mask(thumb_np)
    tissue_mask = tissue_mask.astype(bool)

    candidate_centers = generate_candidate_centers(
        slide_dims=slide.dimensions,
        patch_size=patch_size,
        stride=stride
    )

    kept_centers = keep_centers_far_from_tissue_edge(
        candidate_centers,
        tissue_mask,
        full_size=slide.dimensions,
        thumb_size=thumb.size,
        patch_size=patch_size,
        min_tissue_ratio=0.6,
        min_edge_distance_thumb=2,
    )

    tumor_centers = []
    normal_centers = []

    if xml_path is not None and xml_path.exists():
        polygons = parse_polygons_from_xml(str(xml_path))
        polygon_paths = build_polygon_paths(polygons)

        for x, y in kept_centers:
            if point_in_any_polygon(x, y, polygon_paths):
                tumor_centers.append((x, y))
            elif not point_near_tumor(x, y, polygon_paths, margin=300) :
                normal_centers.append((x, y))
    else:
        normal_centers = kept_centers.copy()

    if max_tumor_per_slide is not None and len(tumor_centers) > max_tumor_per_slide:
        tumor_centers = random.sample(tumor_centers, max_tumor_per_slide)

    print("Candidats totaux :", len(candidate_centers))
    print("Dans le tissu    :", len(kept_centers))
    print("Tumor candidats  :", len(tumor_centers))
    print("Normal candidats :", len(normal_centers))

    slide_name = wsi_path.stem
    saved_tumor = 0
    saved_normal = 0

    # Cas lame tumorale annotée
    if len(tumor_centers) > 0:
        if balance_normal_to_tumor:
            n_normal = min(len(normal_centers), len(tumor_centers))
            normal_sample = random.sample(normal_centers, n_normal) if n_normal > 0 else []
        else:
            normal_sample = normal_centers

        for cx, cy in tumor_centers:
            patch = extract_patch(slide, cx, cy, patch_size=patch_size, level=0)
            if is_informative_patch(
                patch,
                white_threshold=WHITE_THRESHOLD,
                min_tissue_ratio=MIN_TISSUE_RATIO
            ):
                save_patch(patch, "tumor", slide_name, cx, cy)
                saved_tumor += 1

        for cx, cy in normal_sample:
            patch = extract_patch(slide, cx, cy, patch_size=patch_size, level=0)
            if is_informative_patch(
                patch,
                white_threshold=WHITE_THRESHOLD,
                min_tissue_ratio=MIN_TISSUE_RATIO
            ):
                save_patch(patch, "normal", slide_name, cx, cy)
                saved_normal += 1

    # Cas lame normale
    else:
        if max_normal_per_slide is not None and len(normal_centers) > max_normal_per_slide:
            normal_sample = random.sample(normal_centers, max_normal_per_slide)
        else:
            normal_sample = normal_centers

        for cx, cy in normal_sample:
            patch = extract_patch(slide, cx, cy, patch_size=patch_size, level=0)
            if is_informative_patch(
                patch,
                white_threshold=WHITE_THRESHOLD,
                min_tissue_ratio=MIN_TISSUE_RATIO
            ):
                save_patch(patch, "normal", slide_name, cx, cy)
                saved_normal += 1

    slide.close()

    print("Tumor sauvegardés :", saved_tumor)
    print("Normal sauvegardés:", saved_normal)

    return saved_tumor, saved_normal


def main():
    tumor_files = sorted(
        [p for p in WSI_DIR.glob("tumor_*.tif") if not is_hidden_mac_file(p)]
    )[:MAX_TUMOR_SLIDES]

    normal_files = sorted(
        [p for p in WSI_DIR.glob("normal_*.tif") if not is_hidden_mac_file(p)]
    )[:MAX_NORMAL_SLIDES]

    wsi_files = tumor_files + normal_files

    if not wsi_files:
        raise FileNotFoundError(f"Aucune WSI trouvée dans {WSI_DIR}")

    total_tumor = 0
    total_normal = 0

    for wsi_path in wsi_files:
        xml_path = ANNOTATIONS_DIR / f"{wsi_path.stem}.xml"

        if xml_path.exists():
            print(f"Annotation trouvée pour {wsi_path.name}")
            n_tumor, n_normal = process_slide(
                wsi_path=wsi_path,
                xml_path=xml_path,
                patch_size=PATCH_SIZE,
                stride=STRIDE,
                max_normal_per_slide=None,
                max_tumor_per_slide=MAX_TUMOR_PER_TUMOR_SLIDE,
                balance_normal_to_tumor=BALANCE_NORMAL_TO_TUMOR,
            )
        else:
            print(f"Pas d'annotation pour {wsi_path.name}")
            n_tumor, n_normal = process_slide(
                wsi_path=wsi_path,
                xml_path=None,
                patch_size=PATCH_SIZE,
                stride=STRIDE,
                max_normal_per_slide=MAX_NORMAL_PER_NORMAL_SLIDE,
                max_tumor_per_slide=None,
                balance_normal_to_tumor=False,
            )

        total_tumor += n_tumor
        total_normal += n_normal

    print("\n=== RÉSUMÉ FINAL ===")
    print("Total tumor sauvegardés :", total_tumor)
    print("Total normal sauvegardés :", total_normal)


if __name__ == "__main__":
    main()