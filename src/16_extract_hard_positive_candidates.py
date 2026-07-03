from pathlib import Path
import argparse
import csv
import xml.etree.ElementTree as ET

import openslide
from matplotlib.path import Path as MplPath
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data/inference_iter2"
WSI_DIR = PROJECT_ROOT / "data/wsi"
ANNOTATION_DIR = PROJECT_ROOT / "data/annotations"
OUTPUT_DIR = PROJECT_ROOT / "outputs/hard_positive_review_iter2"
PATCH_OUTPUT_DIR = PROJECT_ROOT / "data/review/hard_positive_iter2"

DEFAULT_SLIDES = [f"tumor_{i:03d}" for i in range(1, 11)]


def read_probs(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "x": int(float(row["x"])),
                    "y": int(float(row["y"])),
                    "prob": float(row["prob_tumor"]),
                }
            )
    return rows


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
            poly.append((float(coord.attrib["X"]), float(coord.attrib["Y"])))

        if len(poly) >= 3:
            polygons.append(poly)

    return polygons


def build_polygon_paths(polygons):
    return [MplPath(poly) for poly in polygons]


def point_in_any_polygon(x, y, paths):
    return any(path.contains_point((x, y)) for path in paths)


def point_near_polygon_edge(x, y, paths, margin):
    if not point_in_any_polygon(x, y, paths):
        return False

    offsets = [(margin, 0), (-margin, 0), (0, margin), (0, -margin)]
    return any(
        not point_in_any_polygon(x + dx, y + dy, paths)
        for dx, dy in offsets
    )


def points_in_any_polygon(points, paths):
    if len(points) == 0:
        return np.zeros(0, dtype=bool)

    mask = np.zeros(len(points), dtype=bool)
    for path in paths:
        mask |= path.contains_points(points)
    return mask


def classify_candidate(prob, near_edge, low_threshold, mid_threshold):
    if prob <= low_threshold:
        return "low_prob_edge" if near_edge else "low_prob"
    if prob <= mid_threshold:
        return "mid_prob_edge" if near_edge else "mid_prob"
    if near_edge:
        return "edge_high_prob"
    return None


def extract_patch(slide, center_x, center_y, patch_size):
    half = patch_size // 2
    return slide.read_region(
        (center_x - half, center_y - half),
        0,
        (patch_size, patch_size),
    ).convert("RGB")


def annotate_patch(patch, label):
    canvas = Image.new("RGB", (patch.width, patch.height + 30), "white")
    canvas.paste(patch, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, patch.height, patch.width, patch.height + 30), fill="white")
    draw.text(
        (6, patch.height + 8),
        label,
        fill=(20, 20, 20),
        font=ImageFont.load_default(),
    )
    return canvas


def save_contact_sheet(patches, output_path, columns=4, pad=8):
    if not patches:
        return

    tile_w, tile_h = patches[0].size
    rows = (len(patches) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (
            columns * tile_w + (columns + 1) * pad,
            rows * tile_h + (rows + 1) * pad,
        ),
        "white",
    )

    for idx, patch in enumerate(patches):
        col = idx % columns
        row = idx // columns
        x = pad + col * (tile_w + pad)
        y = pad + row * (tile_h + pad)
        sheet.paste(patch, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def save_slide_overview(slide, polygons, candidate_rows, output_path, thumbnail_size=(1600, 1600)):
    thumb = slide.get_thumbnail(thumbnail_size).convert("RGB")
    draw = ImageDraw.Draw(thumb)
    full_w, full_h = slide.dimensions
    scale_x = thumb.width / full_w
    scale_y = thumb.height / full_h

    for poly in polygons:
        points = [(int(x * scale_x), int(y * scale_y)) for x, y in poly]
        if len(points) >= 2:
            draw.line(points + [points[0]], fill=(40, 120, 230), width=3)

    for idx, row in enumerate(candidate_rows, start=1):
        x = int(row["x"] * scale_x)
        y = int(row["y"] * scale_y)
        r = 7
        color = (230, 30, 30) if row["category"].startswith("low") else (240, 140, 20)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=color, width=3)
        draw.text((x + 8, y - 8), str(idx), fill=color, font=ImageFont.load_default())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    thumb.save(output_path)


def select_candidates(candidates, max_per_slide):
    category_order = {
        "low_prob_edge": 0,
        "low_prob": 1,
        "mid_prob_edge": 2,
        "mid_prob": 3,
        "edge_high_prob": 4,
    }
    ranked = sorted(
        candidates,
        key=lambda r: (category_order.get(r["category"], 99), r["prob"]),
    )
    return ranked[:max_per_slide]


def write_csv(path, rows):
    fieldnames = [
        "slide_id",
        "candidate_id",
        "category",
        "prob",
        "x",
        "y",
        "patch_path",
        "contact_sheet",
        "overview",
        "review_category",
        "include_as_hard_positive",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, rows, slide_stats, args):
    lines = [
        "# Hard Positive Candidate Review",
        "",
        f"Model inference CSV directory: `{args.csv_dir}`",
        f"Low probability threshold: `{args.low_threshold}`",
        f"Mid probability threshold: `{args.mid_threshold}`",
        f"Edge margin: `{args.edge_margin}` pixels",
        f"Maximum selected candidates per slide: `{args.max_candidates_per_slide}`",
        "",
        f"Selected candidates: `{len(rows)}`",
        "",
        "| Slide | Annotated tumor candidates | Eligible hard positives | Selected | Lowest prob |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for slide_id in sorted(slide_stats):
        stat = slide_stats[slide_id]
        lowest = stat["lowest_prob"]
        lowest_text = f"{lowest:.3f}" if lowest is not None else ""
        lines.append(
            f"| {slide_id} | {stat['tumor_rows']} | {stat['eligible']} | "
            f"{stat['selected']} | {lowest_text} |"
        )

    lines.extend(
        [
            "",
            "Review goal: confirm which low/intermediate-probability tumor patches",
            "are true tumor and useful as hard positives for a future iter5 dataset.",
            "Border candidates are included because they may represent small tumor",
            "clusters, partial tumor, crush artefact, fibrosis, necrosis, or transition",
            "zones that are clinically useful for robust training.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract hard-positive tumor candidates from annotated WSI regions."
    )
    parser.add_argument("--csv-dir", default=str(CSV_DIR))
    parser.add_argument("--wsi-dir", default=str(WSI_DIR))
    parser.add_argument("--annotation-dir", default=str(ANNOTATION_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--patch-output-dir", default=str(PATCH_OUTPUT_DIR))
    parser.add_argument("--slides", nargs="+", default=DEFAULT_SLIDES)
    parser.add_argument("--low-threshold", type=float, default=0.50)
    parser.add_argument("--mid-threshold", type=float, default=0.80)
    parser.add_argument("--edge-margin", type=int, default=256)
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--max-candidates-per-slide", type=int, default=24)
    return parser.parse_args()


def main():
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    wsi_dir = Path(args.wsi_dir)
    annotation_dir = Path(args.annotation_dir)
    output_dir = Path(args.output_dir)
    patch_output_dir = Path(args.patch_output_dir)

    all_rows = []
    slide_stats = {}

    for slide_id in args.slides:
        csv_path = csv_dir / f"{slide_id}_probs.csv"
        wsi_path = wsi_dir / f"{slide_id}.tif"
        xml_path = annotation_dir / f"{slide_id}.xml"

        if not csv_path.exists():
            print("CSV manquant, skip:", csv_path)
            continue
        if not wsi_path.exists():
            print("WSI manquante, skip:", wsi_path)
            continue
        if not xml_path.exists():
            print("Annotation manquante, skip:", xml_path)
            continue

        polygons = parse_polygons_from_xml(xml_path)
        paths = build_polygon_paths(polygons)
        rows = read_probs(csv_path)

        points = np.array([(row["x"], row["y"]) for row in rows], dtype=float)
        inside_mask = points_in_any_polygon(points, paths)
        shifted_masks = []
        for dx, dy in [
            (args.edge_margin, 0),
            (-args.edge_margin, 0),
            (0, args.edge_margin),
            (0, -args.edge_margin),
        ]:
            shifted = points + np.array([dx, dy], dtype=float)
            shifted_masks.append(points_in_any_polygon(shifted, paths))
        near_edge_mask = inside_mask & ~np.logical_and.reduce(shifted_masks)

        candidates = []
        tumor_rows = int(inside_mask.sum())
        for row, inside, near_edge in zip(rows, inside_mask, near_edge_mask):
            if not inside:
                continue
            category = classify_candidate(
                row["prob"],
                bool(near_edge),
                args.low_threshold,
                args.mid_threshold,
            )
            if category is None:
                continue
            candidate = dict(row)
            candidate["slide_id"] = slide_id
            candidate["category"] = category
            candidates.append(candidate)

        selected = select_candidates(candidates, args.max_candidates_per_slide)
        print(
            f"{slide_id}: {len(selected)} candidat(s) selectionne(s) "
            f"sur {len(candidates)} eligibles / {tumor_rows} tumor annotes"
        )

        slide_stats[slide_id] = {
            "tumor_rows": tumor_rows,
            "eligible": len(candidates),
            "selected": len(selected),
            "lowest_prob": min((row["prob"] for row in selected), default=None),
        }

        if not selected:
            continue

        slide = openslide.OpenSlide(str(wsi_path))
        slide_dir = patch_output_dir / slide_id
        slide_dir.mkdir(parents=True, exist_ok=True)
        annotated_patches = []
        overview_path = slide_dir / f"{slide_id}_overview.png"
        contact_sheet_path = slide_dir / f"{slide_id}_hard_positive_contact_sheet.png"

        for candidate_id, row in enumerate(selected, start=1):
            patch = extract_patch(slide, row["x"], row["y"], args.patch_size)
            patch_name = (
                f"{slide_id}_hp{candidate_id:02d}_{row['category']}"
                f"_prob{row['prob']:.3f}_x{row['x']}_y{row['y']}.png"
            )
            patch_path = slide_dir / patch_name
            patch.save(patch_path)

            label = (
                f"HP{candidate_id} {row['category']} "
                f"p={row['prob']:.3f} x={row['x']} y={row['y']}"
            )
            annotated_patches.append(annotate_patch(patch, label))

            out_row = {
                "slide_id": slide_id,
                "candidate_id": candidate_id,
                "category": row["category"],
                "prob": row["prob"],
                "x": row["x"],
                "y": row["y"],
                "patch_path": str(patch_path),
                "contact_sheet": str(contact_sheet_path),
                "overview": str(overview_path),
                "review_category": "",
                "include_as_hard_positive": "",
                "notes": "",
            }
            all_rows.append(out_row)

        save_contact_sheet(annotated_patches, contact_sheet_path)
        save_slide_overview(slide, polygons, selected, overview_path)
        slide.close()

    write_csv(output_dir / "review_template.csv", all_rows)
    write_csv(output_dir / "candidates.csv", all_rows)
    write_summary(output_dir / "summary.md", all_rows, slide_stats, args)

    print("Candidats sauvegardes:", output_dir / "candidates.csv")
    print("Template de revue sauvegarde:", output_dir / "review_template.csv")
    print("Resume sauvegarde:", output_dir / "summary.md")
    print("Patches sauvegardes:", patch_output_dir)


if __name__ == "__main__":
    main()
