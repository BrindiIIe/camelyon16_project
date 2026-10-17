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


WSI_PATH = "../data/wsi/tumor_001.tif"


def keep_largest_components(mask, n=2):
    labeled = label(mask)
    regions = regionprops(labeled)

    if len(regions) == 0:
        return mask

    regions = sorted(regions, key=lambda r: r.area, reverse=True)
    keep_labels = [r.label for r in regions[:n]]

    cleaned = np.isin(labeled, keep_labels)
    return cleaned


def clear_border_margin(mask, margin=20):
    """
    Supprime une bande périphérique pour virer les bords gris de lame.
    """
    cleaned = mask.copy()
    cleaned[:margin, :] = False
    cleaned[-margin:, :] = False
    cleaned[:, :margin] = False
    cleaned[:, -margin:] = False
    return cleaned


def make_tissue_mask(rgb_image):
    # niveaux de gris
    gray = rgb2gray(rgb_image)

    # seuillage automatique type Otsu :
    # tissu plus sombre que le fond
    thr = threshold_otsu(gray)
    raw = gray < thr

    # enlever une petite bande périphérique
    raw = clear_border_margin(raw, margin=25)

    # morphologie : enlever petits objets puis consolider les gros
    mask = remove_small_objects(raw, min_size=500)
    mask = binary_closing(mask, disk(8))
    mask = binary_fill_holes(mask)
    mask = binary_opening(mask, disk(3))

    # garder seulement les plus grosses masses
    mask = keep_largest_components(mask, n=5)

    # petit nettoyage final
    # mask = binary_erosion(mask, disk(1))
    mask = binary_dilation(mask, disk(3))

    return raw, mask, thr


def make_clean_tissue_mask(rgb_image):
    """
    Return only the cleaned tissue mask used for patch selection.

    Keeping this accessor separate avoids accidentally selecting the first
    element of ``make_tissue_mask()``, which is the diagnostic raw Otsu mask.
    """
    _, cleaned_mask, _ = make_tissue_mask(rgb_image)
    return cleaned_mask


def main():
    from pathlib import Path

    import openslide
    import matplotlib.pyplot as plt

    if not Path(WSI_PATH).exists():
        raise FileNotFoundError(f"WSI introuvable: {WSI_PATH}")

    slide = openslide.OpenSlide(WSI_PATH)
    thumb = slide.get_thumbnail((1200, 1200)).convert("RGB")
    thumb_np = np.array(thumb)

    raw_mask, cleaned_mask, thr = make_tissue_mask(thumb_np)

    print("Seuil Otsu:", thr)
    print("Pixels raw:", raw_mask.sum())
    print("Pixels cleaned:", cleaned_mask.sum())

    plt.figure(figsize=(8, 8))
    plt.imshow(thumb_np)
    plt.title("Thumbnail")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.imshow(raw_mask, cmap="gray")
    plt.title("Masque brut (Otsu)")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.imshow(cleaned_mask, cmap="gray")
    plt.title("Masque nettoyé")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.imshow(thumb_np)
    plt.imshow(cleaned_mask, cmap="Reds", alpha=0.35)
    plt.title("Overlay tissu")
    plt.axis("off")
    plt.show()

    slide.close()


if __name__ == "__main__":
    main()
