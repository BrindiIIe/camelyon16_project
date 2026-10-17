from pathlib import Path
import argparse
import csv

import matplotlib
import numpy as np
import openslide

from tissue_mask import make_tissue_mask


matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Export side-by-side raw and cleaned tissue-mask overlays for "
            "visual WSI audit."
        )
    )
    parser.add_argument(
        "--wsi-dir", default=str(PROJECT_ROOT / "data" / "wsi")
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "tissue_mask_audit"),
    )
    parser.add_argument("--slides", nargs="+", required=True)
    parser.add_argument("--thumb-size", type=int, default=1200)
    return parser.parse_args()


def export_slide(wsi_path, output_dir, thumb_size):
    slide = openslide.OpenSlide(str(wsi_path))
    thumbnail = slide.get_thumbnail((thumb_size, thumb_size)).convert("RGB")
    slide.close()

    rgb = np.asarray(thumbnail)
    raw, cleaned, threshold = make_tissue_mask(rgb)
    added = cleaned & ~raw
    removed = raw & ~cleaned

    figure, axes = plt.subplots(2, 2, figsize=(14, 12), constrained_layout=True)
    axes[0, 0].imshow(rgb)
    axes[0, 0].set_title(f"{wsi_path.stem} — miniature WSI")

    axes[0, 1].imshow(rgb)
    axes[0, 1].imshow(raw, cmap="Reds", alpha=0.38, interpolation="nearest")
    axes[0, 1].set_title("Masque brut Otsu (rouge)")

    axes[1, 0].imshow(rgb)
    axes[1, 0].imshow(
        cleaned, cmap="Blues", alpha=0.40, interpolation="nearest"
    )
    axes[1, 0].set_title("Masque nettoyé utilisé (bleu)")

    delta = np.zeros((*raw.shape, 4), dtype=np.float32)
    delta[added] = (0.0, 0.75, 0.2, 0.60)
    delta[removed] = (1.0, 0.1, 0.1, 0.65)
    axes[1, 1].imshow(rgb)
    axes[1, 1].imshow(delta, interpolation="nearest")
    axes[1, 1].set_title("Différence : ajouté vert, retiré rouge")

    for axis in axes.flat:
        axis.axis("off")

    output_path = output_dir / f"{wsi_path.stem}_mask_audit.png"
    figure.suptitle(
        (
            f"Audit masque tissulaire — seuil Otsu {threshold:.4f} | "
            f"brut {raw.mean():.1%} | nettoyé {cleaned.mean():.1%}"
        ),
        fontsize=16,
        fontweight="bold",
    )
    figure.savefig(output_path, dpi=150, facecolor="white")
    plt.close(figure)

    return {
        "slide_id": wsi_path.stem,
        "thumbnail_width": rgb.shape[1],
        "thumbnail_height": rgb.shape[0],
        "otsu_threshold": threshold,
        "raw_pixels": int(raw.sum()),
        "cleaned_pixels": int(cleaned.sum()),
        "added_pixels": int(added.sum()),
        "removed_pixels": int(removed.sum()),
        "raw_fraction": float(raw.mean()),
        "cleaned_fraction": float(cleaned.mean()),
        "audit_image": str(output_path),
    }


def main():
    args = parse_args()
    wsi_dir = Path(args.wsi_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for slide_id in args.slides:
        wsi_path = wsi_dir / f"{slide_id}.tif"
        if not wsi_path.exists():
            raise FileNotFoundError(wsi_path)
        row = export_slide(wsi_path, output_dir, args.thumb_size)
        rows.append(row)
        print(
            f"{slide_id}: raw={row['raw_fraction']:.1%}, "
            f"cleaned={row['cleaned_fraction']:.1%}, "
            f"added={row['added_pixels']:,}, "
            f"removed={row['removed_pixels']:,}"
        )

    summary_path = output_dir / "tissue_mask_audit_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()
