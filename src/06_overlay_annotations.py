from pathlib import Path
import xml.etree.ElementTree as ET

import openslide
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


WSI_PATH = Path("../data/wsi/tumor_001.tif")
XML_PATH = Path("../data/annotations/tumor_001.xml")
OUTPUT_FIG = Path("../data/inference/tumor_001_annotations_overlay.png")

THUMB_SIZE = (1200, 1200)

OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)


def level0_to_thumbnail_coords(x, y, full_size, thumb_size):
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    tx = x * thumb_w / full_w
    ty = y * thumb_h / full_h
    return tx, ty


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


def main():
    if not WSI_PATH.exists():
        raise FileNotFoundError(f"WSI introuvable: {WSI_PATH}")

    if not XML_PATH.exists():
        raise FileNotFoundError(f"XML introuvable: {XML_PATH}")

    slide = openslide.OpenSlide(str(WSI_PATH))
    thumb = slide.get_thumbnail(THUMB_SIZE).convert("RGB")
    thumb_np = np.array(thumb)

    polygons = parse_polygons_from_xml(XML_PATH)

    plt.figure(figsize=(10, 10))
    ax = plt.gca()
    ax.imshow(thumb_np)

    for poly in polygons:
        thumb_poly = [
            level0_to_thumbnail_coords(x, y, slide.dimensions, thumb.size)
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

    plt.title(f"Annotations overlay - {WSI_PATH.name}")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG, dpi=200, bbox_inches="tight")
    plt.show()

    slide.close()
    print("Overlay sauvegardé:", OUTPUT_FIG)


if __name__ == "__main__":
    main()