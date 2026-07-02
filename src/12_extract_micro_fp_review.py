from pathlib import Path
import argparse
import csv
from collections import deque

import openslide
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data/inference_iter2"
WSI_DIR = PROJECT_ROOT / "data/wsi"
OUTPUT_DIR = PROJECT_ROOT / "outputs/micro_fp_review_iter2"
PATCH_OUTPUT_DIR = PROJECT_ROOT / "data/review/micro_fp_iter2"

DEFAULT_SLIDES = [f"normal_{i:03d}" for i in range(1, 11)]


def read_probs(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "x": int(float(row["x"])),
                "y": int(float(row["y"])),
                "prob": float(row["prob_tumor"]),
            })
    return rows


def connected_components(rows, threshold, stride):
    points = {
        (row["x"], row["y"]): row["prob"]
        for row in rows
        if row["prob"] >= threshold
    }
    if not points:
        return []

    offsets = [
        (-stride, -stride), (0, -stride), (stride, -stride),
        (-stride, 0),                     (stride, 0),
        (-stride, stride),  (0, stride),  (stride, stride),
    ]
    visited = set()
    components = []

    for start in points:
        if start in visited:
            continue

        queue = deque([start])
        visited.add(start)
        component = []

        while queue:
            x, y = queue.popleft()
            component.append({"x": x, "y": y, "prob": points[(x, y)]})

            for dx, dy in offsets:
                neighbor = (x + dx, y + dy)
                if neighbor in points and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        components.append(component)

    return components


def component_summary(slide_id, component_id, component):
    xs = [p["x"] for p in component]
    ys = [p["y"] for p in component]
    probs = [p["prob"] for p in component]
    top = max(component, key=lambda p: p["prob"])
    return {
        "slide_id": slide_id,
        "component_id": component_id,
        "n_patches": len(component),
        "max_prob": max(probs),
        "mean_prob": sum(probs) / len(probs),
        "top_x": top["x"],
        "top_y": top["y"],
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def extract_patch(slide, center_x, center_y, patch_size):
    half = patch_size // 2
    return slide.read_region(
        (center_x - half, center_y - half),
        0,
        (patch_size, patch_size),
    ).convert("RGB")


def annotate_patch(patch, label):
    canvas = Image.new("RGB", (patch.width, patch.height + 26), "white")
    canvas.paste(patch, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, patch.height, patch.width, patch.height + 26), fill="white")
    draw.text((6, patch.height + 6), label, fill=(20, 20, 20), font=ImageFont.load_default())
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


def save_slide_overview(slide, component_summaries, output_path, thumbnail_size=(1600, 1600)):
    thumb = slide.get_thumbnail(thumbnail_size).convert("RGB")
    draw = ImageDraw.Draw(thumb)
    full_w, full_h = slide.dimensions
    scale_x = thumb.width / full_w
    scale_y = thumb.height / full_h

    for row in component_summaries:
        x0 = int(row["min_x"] * scale_x)
        y0 = int(row["min_y"] * scale_y)
        x1 = int(row["max_x"] * scale_x)
        y1 = int(row["max_y"] * scale_y)
        margin = 8
        box = (
            max(0, x0 - margin),
            max(0, y0 - margin),
            min(thumb.width - 1, x1 + margin),
            min(thumb.height - 1, y1 + margin),
        )
        draw.rectangle(box, outline=(230, 30, 30), width=4)
        draw.text((box[0] + 4, max(0, box[1] - 14)), f"C{row['component_id']}", fill=(230, 30, 30))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    thumb.save(output_path)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "slide_id",
        "component_id",
        "n_patches",
        "max_prob",
        "mean_prob",
        "top_x",
        "top_y",
        "min_x",
        "min_y",
        "max_x",
        "max_y",
        "patch_dir",
        "contact_sheet",
        "overview",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_review_template(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "slide_id",
        "component_id",
        "n_patches",
        "max_prob",
        "top_x",
        "top_y",
        "contact_sheet",
        "overview",
        "review_category",
        "include_as_hard_negative",
        "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "slide_id": row["slide_id"],
                "component_id": row["component_id"],
                "n_patches": row["n_patches"],
                "max_prob": row["max_prob"],
                "top_x": row["top_x"],
                "top_y": row["top_y"],
                "contact_sheet": row["contact_sheet"],
                "overview": row["overview"],
                "review_category": "",
                "include_as_hard_negative": "",
                "notes": "",
            })


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract normal-slide micro-clusters for visual false-positive review."
    )
    parser.add_argument("--csv-dir", default=str(CSV_DIR))
    parser.add_argument("--wsi-dir", default=str(WSI_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--patch-output-dir", default=str(PATCH_OUTPUT_DIR))
    parser.add_argument("--slides", nargs="+", default=DEFAULT_SLIDES)
    parser.add_argument("--threshold", type=float, default=0.99)
    parser.add_argument("--min-component-size", type=int, default=2)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--max-components-per-slide", type=int, default=8)
    parser.add_argument("--max-patches-per-component", type=int, default=12)
    return parser.parse_args()


def main():
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    wsi_dir = Path(args.wsi_dir)
    output_dir = Path(args.output_dir)
    patch_output_dir = Path(args.patch_output_dir)

    all_rows = []

    for slide_id in args.slides:
        csv_path = csv_dir / f"{slide_id}_probs.csv"
        wsi_path = wsi_dir / f"{slide_id}.tif"

        if not csv_path.exists():
            print("CSV manquant, skip:", csv_path)
            continue
        if not wsi_path.exists():
            print("WSI manquante, skip:", wsi_path)
            continue

        rows = read_probs(csv_path)
        components = connected_components(rows, args.threshold, args.stride)
        components = [c for c in components if len(c) >= args.min_component_size]
        components = sorted(
            components,
            key=lambda c: (len(c), max(p["prob"] for p in c)),
            reverse=True,
        )[:args.max_components_per_slide]

        if not components:
            print(f"{slide_id}: aucun micro-cluster")
            continue

        print(f"{slide_id}: {len(components)} micro-cluster(s)")
        slide = openslide.OpenSlide(str(wsi_path))
        slide_component_rows = []

        for component_id, component in enumerate(components, start=1):
            summary = component_summary(slide_id, component_id, component)
            component_dir = patch_output_dir / slide_id / f"component_{component_id:02d}"
            component_dir.mkdir(parents=True, exist_ok=True)

            selected = sorted(component, key=lambda p: p["prob"], reverse=True)
            selected = selected[:args.max_patches_per_component]
            annotated_patches = []

            for patch_idx, point in enumerate(selected, start=1):
                patch = extract_patch(slide, point["x"], point["y"], args.patch_size)
                label = f"C{component_id} P{patch_idx} p={point['prob']:.3f} x={point['x']} y={point['y']}"
                patch_name = (
                    f"{slide_id}_c{component_id:02d}_p{patch_idx:02d}"
                    f"_prob{point['prob']:.3f}_x{point['x']}_y{point['y']}.png"
                )
                patch.save(component_dir / patch_name)
                annotated_patches.append(annotate_patch(patch, label))

            contact_sheet = component_dir / f"{slide_id}_component_{component_id:02d}_contact_sheet.png"
            save_contact_sheet(annotated_patches, contact_sheet)

            summary["patch_dir"] = str(component_dir)
            summary["contact_sheet"] = str(contact_sheet)
            summary["overview"] = str(patch_output_dir / slide_id / f"{slide_id}_overview.png")
            slide_component_rows.append(summary)
            all_rows.append(summary)

        save_slide_overview(
            slide,
            slide_component_rows,
            patch_output_dir / slide_id / f"{slide_id}_overview.png",
        )
        slide.close()

    write_csv(output_dir / "components.csv", all_rows)
    write_review_template(output_dir / "review_template.csv", all_rows)
    print("Table sauvegardee:", output_dir / "components.csv")
    print("Template de revue sauvegarde:", output_dir / "review_template.csv")
    print("Patches sauvegardes:", patch_output_dir)


if __name__ == "__main__":
    main()
