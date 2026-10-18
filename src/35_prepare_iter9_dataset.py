"""Prepare Iter9 by adding only reviewed hard positives to Iter8."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "patches_iter8" / "train"
OUTPUT_DIR = ROOT / "data" / "patches_iter9" / "train"
PACK = ROOT / "portable_review_packs" / "iter9_hard_positive_review"
CANDIDATES_CSV = ROOT / "outputs" / "iter9_hard_positive_mining" / "candidates.csv"
SPLIT_CSV = ROOT / "outputs" / "splits" / "wsi_split_v1.csv"
SUMMARY_DIR = ROOT / "outputs" / "iter9_dataset"
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}
REQUIRED_REVIEW_FIELDS = [
    "site_diagnosis", "dominant_pattern", "image_quality", "confidence",
    "include_as_hard_positive", "reviewer", "review_date",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Iter9 from Iter8 and the completed hard-positive review."
    )
    parser.add_argument("--review-csv", default=None)
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--summary-dir", default=str(SUMMARY_DIR))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_image(path: Path) -> bool:
    return path.is_file() and not path.name.startswith("._") and path.suffix.lower() in VALID_EXTENSIONS


def count_images(root: Path) -> dict[str, int]:
    result = {}
    for label in ("normal", "tumor"):
        label_dir = root / label
        result[label] = sum(is_image(path) for path in label_dir.rglob("*")) if label_dir.exists() else 0
    result["total"] = result["normal"] + result["tumor"]
    return result


def resolve_review_csv(argument: str | None) -> Path:
    if argument:
        path = Path(argument)
        if not path.is_absolute():
            path = ROOT / path
        return path
    candidates = sorted(PACK.glob("iter9_hard_positive_review_*.csv"))
    completed = PACK / "review_completed.csv"
    if completed.is_file():
        candidates.append(completed)
    if len(candidates) != 1:
        raise ValueError(
            "Place exactly one completed review CSV in the review pack or pass --review-csv. "
            f"Found {len(candidates)}."
        )
    return candidates[0]


def canonical_metadata(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row.get("slide_id", "").strip(),
        str(int(float(row.get("x", "nan")))),
        str(int(float(row.get("y", "nan")))),
        str(int(float(row.get("selection_rank_within_slide", "nan")))),
    )


def validate_review(review_csv: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    source = read_csv(CANDIDATES_CSV)
    reviewed = read_csv(review_csv)
    if len(source) != len(reviewed) or not source or len(source) > 120:
        raise ValueError(f"Review row count mismatch: source={len(source)}, review={len(reviewed)}")
    source_by_id = {row["candidate_id"]: row for row in source}
    if len(source_by_id) != len(source):
        raise ValueError("Duplicate candidate IDs in mining output.")
    reviewed_ids = [row.get("candidate_id", "") for row in reviewed]
    if len(reviewed_ids) != len(set(reviewed_ids)) or set(reviewed_ids) != set(source_by_id):
        raise ValueError("Review candidate IDs differ from the frozen mining selection.")

    split = {row["slide_id"]: row for row in read_csv(SPLIT_CSV)}
    accepted: list[dict[str, str]] = []
    for row in reviewed:
        candidate_id = row["candidate_id"]
        original = source_by_id[candidate_id]
        if canonical_metadata(row) != canonical_metadata(original):
            raise ValueError(f"Modified candidate metadata: {candidate_id}")
        slide = split.get(row["slide_id"], {})
        if slide.get("split") != "train" or slide.get("label") != "tumor":
            raise ValueError(f"Candidate outside tumor training split: {candidate_id}")
        missing = [field for field in REQUIRED_REVIEW_FIELDS if not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"Incomplete review for {candidate_id}: {missing}")
        include = row["include_as_hard_positive"].strip().lower()
        if include not in {"yes", "no"}:
            raise ValueError(f"Invalid inclusion decision for {candidate_id}: {include!r}")
        eligible = (
            row["site_diagnosis"].strip().lower() == "tumor"
            and row["image_quality"].strip().lower() in {"good", "interpretable_with_limitations"}
            and row["confidence"].strip().lower() in {"medium", "high"}
            and row["dominant_pattern"].strip().lower() != "annotation_edge"
        )
        if include == "yes" and not eligible:
            raise ValueError(
                f"Inconsistent inclusion for {candidate_id}: accepted patches require confirmed "
                "tumor, interpretable quality, medium/high confidence, and no annotation edge."
            )
        if include == "yes":
            accepted.append(row)
    if not accepted:
        raise ValueError("No reviewed hard positive meets the pre-specified inclusion rule.")
    return reviewed, accepted


def existing_coordinate_index(source_dir: Path) -> set[tuple[str, str, str]]:
    coordinates: set[tuple[str, str, str]] = set()
    for path in source_dir.rglob("*"):
        if not is_image(path):
            continue
        slide = re.search(r"tumor_\d{3}", path.name)
        xy = re.search(r"_x(\d+)_y(\d+)", path.name)
        if not xy:
            xy = re.search(r"_(\d+)_(\d+)\.[^.]+$", path.name)
        if slide and xy:
            coordinates.add((slide.group(), xy.group(1), xy.group(2)))
    return coordinates


def build_dataset(
    source_dir: Path,
    output_dir: Path,
    accepted: list[dict[str, str]],
    overwrite: bool,
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int]]:
    if output_dir.resolve() != OUTPUT_DIR.resolve():
        raise ValueError("Output must be the dedicated data/patches_iter9/train directory.")
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(f"{output_dir} exists; pass --overwrite to rebuild it.")
        shutil.rmtree(output_dir)
    source_counts = count_images(source_dir)
    if not source_counts["total"]:
        raise ValueError(f"Empty Iter8 dataset: {source_dir}")
    existing = existing_coordinate_index(source_dir)
    shutil.copytree(source_dir, output_dir, ignore=shutil.ignore_patterns("._*", "__pycache__"))
    tumor_dir = output_dir / "tumor"
    added: list[dict[str, str]] = []
    for row in accepted:
        patch = PACK / row["patch_path"]
        if not patch.is_file():
            raise FileNotFoundError(patch)
        dest = tumor_dir / f"iter9_hp_{row['slide_id']}_x{row['x']}_y{row['y']}.png"
        if dest.exists():
            raise FileExistsError(dest)
        shutil.copy2(patch, dest)
        coordinate = (row["slide_id"], str(int(float(row["x"]))), str(int(float(row["y"]))))
        added.append(
            {
                "candidate_id": row["candidate_id"],
                "slide_id": row["slide_id"],
                "x": str(int(float(row["x"]))),
                "y": str(int(float(row["y"]))),
                "iter8_prob": row["iter8_prob"],
                "dominant_pattern": row["dominant_pattern"],
                "image_quality": row["image_quality"],
                "confidence": row["confidence"],
                "already_present_coordinate": "yes" if coordinate in existing else "no",
                "source_patch": str(patch.relative_to(ROOT)),
                "destination": str(dest.relative_to(ROOT)),
                "sha256": sha256(patch),
            }
        )
    output_counts = count_images(output_dir)
    if output_counts["normal"] != source_counts["normal"]:
        raise RuntimeError("Iter9 unexpectedly changed the normal class.")
    if output_counts["tumor"] != source_counts["tumor"] + len(added):
        raise RuntimeError("Unexpected Iter9 tumor count.")
    return added, source_counts, output_counts


def write_summary(
    summary_dir: Path,
    review_csv: Path,
    reviewed: list[dict[str, str]],
    added: list[dict[str, str]],
    source_counts: dict[str, int],
    output_counts: dict[str, int],
) -> None:
    summary_dir.mkdir(parents=True, exist_ok=True)
    with (summary_dir / "added_hard_positives.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(added[0]))
        writer.writeheader()
        writer.writerows(added)
    shutil.copy2(review_csv, summary_dir / "review_snapshot.csv")
    pattern_counts: dict[str, int] = {}
    slide_counts: dict[str, int] = {}
    for row in added:
        pattern_counts[row["dominant_pattern"]] = pattern_counts.get(row["dominant_pattern"], 0) + 1
        slide_counts[row["slide_id"]] = slide_counts.get(row["slide_id"], 0) + 1
    lines = [
        "# Préparation du dataset Iter9", "",
        "Iter9 reprend intégralement Iter8 et ajoute uniquement les hard positives confirmés en revue.", "",
        "## Contrat", "",
        "- Source : `data/patches_iter8/train`", "- Données candidates : WSI tumorales d'entraînement uniquement",
        "- Inclusion : tumeur confirmée, image interprétable, confiance moyenne/élevée, hors bord d'annotation et décision explicite `yes`",
        "- Nouveaux hard négatifs : 0", f"- Sites revus : {len(reviewed)}", f"- Hard positives ajoutés : {len(added)}", "",
        "## Effectifs", "", "| Dataset | Normal | Tumeur | Total |", "|---|---:|---:|---:|",
        f"| Iter8 | {source_counts['normal']} | {source_counts['tumor']} | {source_counts['total']} |",
        f"| Iter9 | {output_counts['normal']} | {output_counts['tumor']} | {output_counts['total']} |", "",
        "## Ajouts par lame", "", "| WSI | Patches |", "|---|---:|",
    ]
    lines.extend(f"| `{slide}` | {count} |" for slide, count in sorted(slide_counts.items()))
    lines.extend(["", "## Ajouts par motif", "", "| Motif | Patches |", "|---|---:|"])
    lines.extend(f"| `{pattern}` | {count} |" for pattern, count in sorted(pattern_counts.items()))
    (summary_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "review_csv": str(review_csv.relative_to(ROOT)) if review_csv.is_relative_to(ROOT) else str(review_csv),
        "review_sha256": sha256(review_csv),
        "reviewed": len(reviewed),
        "accepted": len(added),
        "source_counts": source_counts,
        "output_counts": output_counts,
    }
    (summary_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    review_csv = resolve_review_csv(args.review_csv)
    if not review_csv.is_file():
        raise FileNotFoundError(review_csv)
    reviewed, accepted = validate_review(review_csv)
    added, source_counts, output_counts = build_dataset(
        Path(args.source_dir), Path(args.output_dir), accepted, args.overwrite
    )
    write_summary(
        Path(args.summary_dir), review_csv, reviewed, added, source_counts, output_counts
    )
    print(f"Reviewed sites: {len(reviewed)}")
    print(f"Hard positives added: {len(added)}")
    print(f"Iter8: {source_counts}")
    print(f"Iter9: {output_counts}")


if __name__ == "__main__":
    main()
