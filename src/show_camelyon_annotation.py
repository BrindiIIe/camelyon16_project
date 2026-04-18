import xml.etree.ElementTree as ET
from pathlib import Path

import openslide
import matplotlib.pyplot as plt
from PIL import ImageDraw


# ====== chemins ======
WSI_PATH = "../data/wsi/tumor_001.tif"   # adapte si besoin
XML_PATH = "../data/annotations/tumor_001.xml"


def parse_camelyon_xml(xml_path: str):
    """
    Retourne une liste de polygones.
    Chaque polygone = liste de tuples (x, y) en coordonnées niveau 0.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    polygons = []

    for annotation in root.iter("Annotation"):
        coords_block = annotation.find("Coordinates")
        if coords_block is None:
            continue

        points = []
        for coord in coords_block.findall("Coordinate"):
            x = float(coord.attrib["X"])
            y = float(coord.attrib["Y"])
            points.append((x, y))

        if points:
            polygons.append(points)

    return polygons


def scale_polygon_to_thumbnail(polygon, full_size, thumb_size):
    """
    Convertit un polygone du niveau 0 vers l'échelle du thumbnail.
    """
    full_w, full_h = full_size
    thumb_w, thumb_h = thumb_size

    scale_x = thumb_w / full_w
    scale_y = thumb_h / full_h

    scaled = [(x * scale_x, y * scale_y) for x, y in polygon]
    return scaled

def polygon_bbox(polygon):
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_center(polygon):
    x_min, y_min, x_max, y_max = polygon_bbox(polygon)
    return int((x_min + x_max) / 2), int((y_min + y_max) / 2)


def main():
    if not Path(WSI_PATH).exists():
        raise FileNotFoundError(f"WSI introuvable: {WSI_PATH}")
    if not Path(XML_PATH).exists():
        raise FileNotFoundError(f"XML introuvable: {XML_PATH}")

    slide = openslide.OpenSlide(WSI_PATH)

    print("Dimensions niveau 0 :", slide.dimensions)
    print("Nombre de niveaux   :", slide.level_count)
    print("Dimensions niveaux  :", slide.level_dimensions)

    # thumbnail
    thumb = slide.get_thumbnail((1200, 1200)).convert("RGB")

    # annotations
    polygons = parse_camelyon_xml(XML_PATH)
    print(f"Nombre de polygones trouvés : {len(polygons)}")

    # dessin
    draw = ImageDraw.Draw(thumb)

    centers = []
    for i, poly in enumerate(polygons):
        scaled_poly = scale_polygon_to_thumbnail(
            poly,
            full_size=slide.dimensions,
            thumb_size=thumb.size
        )
        draw.line(scaled_poly + [scaled_poly[0]], width=3, fill="red")

        cx, cy = polygon_center(poly)
        centers.append((cx, cy))

        # dessiner aussi le centre sur le thumbnail
        sx = cx * thumb.size[0] / slide.dimensions[0]
        sy = cy * thumb.size[1] / slide.dimensions[1]
        r = 6
        draw.ellipse((sx-r, sy-r, sx+r, sy+r), outline="yellow", width=3)

        print(f"Polygone {i}: centre niveau 0 = ({cx}, {cy})")

    # affichage
    plt.figure(figsize=(10, 10))
    plt.imshow(thumb)
    plt.title("CAMELYON16 - thumbnail avec annotations tumorales")
    plt.axis("off")
    plt.show()

    cx, cy = centers[0]
    patch_size = 512

    top_left_x = cx - patch_size // 2
    top_left_y = cy - patch_size // 2

    patch = slide.read_region((top_left_x, top_left_y), 0, (patch_size, patch_size)).convert("RGB")

    plt.figure(figsize=(6, 6))
    plt.imshow(patch)
    plt.title("Patch centré sur le polygone 0")
    plt.axis("off")
    plt.show()

    slide.close()


if __name__ == "__main__":
    main()