from pathlib import Path
import argparse
import csv

import numpy as np
import openslide

from tissue_mask import make_clean_tissue_mask
from tissue_utils import generate_candidate_centers, keep_centers_in_tissue


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Seed resumable WSI inference with existing probabilities that fall "
            "inside the cleaned tissue mask."
        )
    )
    parser.add_argument("--source-csv-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--wsi-dir", default=str(PROJECT_ROOT / "data" / "wsi")
    )
    parser.add_argument("--slides", nargs="+", required=True)
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--thumb-size", type=int, default=1200)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def seed_slide(args, slide_id):
    source_path = Path(args.source_csv_dir) / f"{slide_id}_probs.csv"
    output_dir = Path(args.output_dir)
    partial_path = output_dir / f"{slide_id}_probs.partial.csv"
    final_path = output_dir / f"{slide_id}_probs.csv"
    wsi_path = Path(args.wsi_dir) / f"{slide_id}.tif"

    if final_path.exists() and not args.overwrite:
        print(f"{slide_id}: final CSV already exists, skip")
        return None
    if partial_path.exists() and not args.overwrite:
        print(f"{slide_id}: partial CSV already exists, skip")
        return None
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if not wsi_path.exists():
        raise FileNotFoundError(wsi_path)

    slide = openslide.OpenSlide(str(wsi_path))
    thumbnail = slide.get_thumbnail(
        (args.thumb_size, args.thumb_size)
    ).convert("RGB")
    cleaned_mask = make_clean_tissue_mask(np.array(thumbnail)).astype(bool)
    candidate_centers = generate_candidate_centers(
        slide_dims=slide.dimensions,
        patch_size=args.patch_size,
        stride=args.stride,
    )
    clean_centers = keep_centers_in_tissue(
        candidate_centers,
        cleaned_mask,
        full_size=slide.dimensions,
        thumb_size=thumbnail.size,
        patch_size=args.patch_size,
    )
    clean_center_set = set(clean_centers)
    slide.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    reused = set()
    source_rows = 0

    with open(source_path, "r", newline="", encoding="utf-8") as source_file:
        reader = csv.DictReader(source_file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {source_path}")
        with open(
            partial_path, "w", newline="", encoding="utf-8"
        ) as partial_file:
            writer = csv.DictWriter(partial_file, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                source_rows += 1
                center = (int(float(row["x"])), int(float(row["y"])))
                if center in clean_center_set:
                    writer.writerow(row)
                    reused.add(center)

    missing = len(clean_center_set - reused)
    result = {
        "slide_id": slide_id,
        "source_rows": source_rows,
        "clean_target_centers": len(clean_center_set),
        "reused_centers": len(reused),
        "missing_centers_for_resume": missing,
        "reuse_fraction": (
            len(reused) / len(clean_center_set) if clean_center_set else 1.0
        ),
        "partial_csv": str(partial_path),
    }
    print(
        f"{slide_id}: target={result['clean_target_centers']} "
        f"reused={result['reused_centers']} missing={missing}"
    )
    return result


def main():
    args = parse_args()
    results = []
    for slide_id in args.slides:
        result = seed_slide(args, slide_id)
        if result is not None:
            results.append(result)

    if not results:
        return

    summary_path = Path(args.output_dir) / "clean_mask_resume_seed_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()
