from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("TORCH_HOME", str(ROOT / ".torch_cache"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib_cache"))

import numpy as np
import openslide
import torch
from matplotlib.path import Path as PolygonPath
from PIL import Image
from torch import nn
from torchvision import models, transforms


SPLIT_CSV = ROOT / "outputs" / "splits" / "wsi_split_v1.csv"
MODEL_PATH = ROOT / "models" / "best_resnet18_patch_iter8.pt"
WSI_DIR = ROOT / "data" / "wsi"
ANNOTATION_DIR = ROOT / "data" / "annotations"
OUTPUT_DIR = ROOT / "outputs" / "iter9_hard_positive_mining"
SCORED_DIR = OUTPUT_DIR / "scored"
EXPECTED_MODEL_SHA256 = "00c243996e6ea1ae402a4be709624f2d1a7a4d4e3f7d0d9a9c675f517b7b2eed"

PATCH_SIZE = 256
GRID_STRIDE = 256
COVERAGE_OFFSET = 96
PROBABILITY_THRESHOLD = 0.25
MIN_NONWHITE_RATIO = 0.50
MIN_SPATIAL_DISTANCE = 1024.0
MAX_PER_SLIDE = 3
MAX_TOTAL = 120


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mine Iter8 false-negative patches from annotated training tumor WSI."
    )
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-slides", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError("fieldnames are required for an empty CSV")
        fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status(state: str, **details: object) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": state,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        **details,
    }
    (OUTPUT_DIR / "status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def resolve_device(requested: str) -> str:
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    return requested


def build_model(device: str):
    actual_hash = sha256(MODEL_PATH)
    if actual_hash != EXPECTED_MODEL_SHA256:
        raise ValueError(f"Unexpected Iter8 checkpoint hash: {actual_hash}")
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()
    return model


def parse_annotations(path: Path) -> dict[str, list[np.ndarray]]:
    regions: dict[str, list[np.ndarray]] = {"Tumor": [], "Exclusion": []}
    for annotation in ET.parse(path).iter("Annotation"):
        group = annotation.get("PartOfGroup")
        if group not in regions:
            raise ValueError(f"Unknown annotation group {group!r} in {path}")
        coordinates = sorted(
            annotation.findall("./Coordinates/Coordinate"),
            key=lambda coordinate: int(coordinate.get("Order", "0")),
        )
        points = np.array(
            [(float(c.get("X")), float(c.get("Y"))) for c in coordinates],
            dtype=np.float64,
        )
        if len(points) < 3:
            raise ValueError(f"Invalid polygon in {path}")
        regions[group].append(points)
    if not regions["Tumor"]:
        raise ValueError(f"No tumor annotation in {path}")
    return regions


def inside_annotations(points: np.ndarray, regions: dict[str, list[np.ndarray]]) -> np.ndarray:
    masks: dict[str, np.ndarray] = {}
    for group, shapes in regions.items():
        mask = np.zeros(len(points), dtype=bool)
        for shape in shapes:
            candidate = np.flatnonzero(
                np.all((points >= shape.min(axis=0)) & (points <= shape.max(axis=0)), axis=1)
            )
            if len(candidate):
                mask[candidate] |= PolygonPath(shape).contains_points(points[candidate])
        masks[group] = mask
    return masks["Tumor"] & ~masks["Exclusion"]


def grid_for_regions(
    slide_dimensions: tuple[int, int], regions: dict[str, list[np.ndarray]]
) -> np.ndarray:
    width, height = slide_dimensions
    half = PATCH_SIZE // 2
    centers: set[tuple[int, int]] = set()
    for shape in regions["Tumor"]:
        min_x = max(half, int(math.floor(shape[:, 0].min())))
        max_x = min(width - half - 1, int(math.ceil(shape[:, 0].max())))
        min_y = max(half, int(math.floor(shape[:, 1].min())))
        max_y = min(height - half - 1, int(math.ceil(shape[:, 1].max())))
        start_x = half + math.ceil((min_x - half) / GRID_STRIDE) * GRID_STRIDE
        start_y = half + math.ceil((min_y - half) / GRID_STRIDE) * GRID_STRIDE
        for y in range(start_y, max_y + 1, GRID_STRIDE):
            for x in range(start_x, max_x + 1, GRID_STRIDE):
                centers.add((x, y))
    if not centers:
        return np.empty((0, 2), dtype=np.int64)
    return np.array(sorted(centers, key=lambda xy: (xy[1], xy[0])), dtype=np.int64)


def keep_annotation_core(
    centers: np.ndarray, regions: dict[str, list[np.ndarray]]
) -> np.ndarray:
    if len(centers) == 0:
        return centers
    masks = []
    for dx, dy in (
        (0, 0),
        (COVERAGE_OFFSET, 0),
        (-COVERAGE_OFFSET, 0),
        (0, COVERAGE_OFFSET),
        (0, -COVERAGE_OFFSET),
    ):
        shifted = centers.astype(np.float64) + np.array([dx, dy], dtype=np.float64)
        masks.append(inside_annotations(shifted, regions))
    return centers[np.logical_and.reduce(masks)]


def nonwhite_ratio(image: Image.Image) -> float:
    array = np.asarray(image, dtype=np.uint8)
    gray = array.mean(axis=2)
    return float((gray < 220).mean())


def score_slide(
    slide_id: str,
    model,
    device: str,
    batch_size: int,
) -> list[dict[str, object]]:
    wsi_path = WSI_DIR / f"{slide_id}.tif"
    annotation_path = ANNOTATION_DIR / f"{slide_id}.xml"
    if not wsi_path.is_file() or not annotation_path.is_file():
        raise FileNotFoundError(f"Missing WSI or annotation for {slide_id}")

    regions = parse_annotations(annotation_path)
    slide = openslide.OpenSlide(str(wsi_path))
    centers = keep_annotation_core(grid_for_regions(slide.dimensions, regions), regions)
    transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
    rows: list[dict[str, object]] = []
    images: list[torch.Tensor] = []
    metadata: list[tuple[int, int, float]] = []

    def flush() -> None:
        if not images:
            return
        batch = torch.stack(images).to(device)
        with torch.inference_mode():
            probabilities = torch.softmax(model(batch), dim=1)[:, 1].cpu().numpy()
        for (x, y, tissue_ratio), probability in zip(metadata, probabilities):
            rows.append(
                {
                    "slide_id": slide_id,
                    "x": x,
                    "y": y,
                    "prob_tumor": float(probability),
                    "nonwhite_ratio": tissue_ratio,
                }
            )
        images.clear()
        metadata.clear()

    try:
        half = PATCH_SIZE // 2
        for x_raw, y_raw in centers:
            x, y = int(x_raw), int(y_raw)
            patch = slide.read_region(
                (x - half, y - half), 0, (PATCH_SIZE, PATCH_SIZE)
            ).convert("RGB")
            tissue_ratio = nonwhite_ratio(patch)
            if tissue_ratio < MIN_NONWHITE_RATIO:
                continue
            images.append(transform(patch))
            metadata.append((x, y, tissue_ratio))
            if len(images) >= batch_size:
                flush()
        flush()
    finally:
        slide.close()
    return rows


def spatially_select(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(rows, key=lambda row: float(row["prob_tumor"]))
    selected: list[dict[str, str]] = []
    for row in ordered:
        if float(row["prob_tumor"]) >= PROBABILITY_THRESHOLD:
            break
        xy = np.array([float(row["x"]), float(row["y"])])
        if any(
            np.linalg.norm(xy - np.array([float(other["x"]), float(other["y"])]))
            < MIN_SPATIAL_DISTANCE
            for other in selected
        ):
            continue
        selected.append(row)
        if len(selected) == MAX_PER_SLIDE:
            break
    return selected


def build_selection(train_slides: list[str]) -> list[dict[str, object]]:
    per_slide: dict[str, list[dict[str, str]]] = {}
    for slide_id in train_slides:
        score_path = SCORED_DIR / f"{slide_id}.csv"
        if not score_path.is_file():
            continue
        per_slide[slide_id] = spatially_select(read_csv(score_path))

    selected: list[dict[str, object]] = []
    for rank in range(MAX_PER_SLIDE):
        candidates = [
            rows[rank]
            for slide_id, rows in sorted(per_slide.items())
            if len(rows) > rank
        ]
        candidates.sort(key=lambda row: float(row["prob_tumor"]))
        for row in candidates:
            selected.append(
                {
                    "candidate_id": f"{row['slide_id']}_iter9_hp_{rank + 1:02d}",
                    "slide_id": row["slide_id"],
                    "x": int(float(row["x"])),
                    "y": int(float(row["y"])),
                    "iter8_prob": float(row["prob_tumor"]),
                    "nonwhite_ratio": float(row["nonwhite_ratio"]),
                    "selection_rank_within_slide": rank + 1,
                    "patch_path": "",
                    "review_image": "",
                    "site_diagnosis": "",
                    "dominant_pattern": "",
                    "image_quality": "",
                    "confidence": "",
                    "include_as_hard_positive": "",
                    "reviewer": "",
                    "review_date": "",
                    "notes": "",
                }
            )
            if len(selected) == MAX_TOTAL:
                return selected
    return selected


def write_summary(
    train_slides: list[str], processed_slides: list[str], selected: list[dict[str, object]]
) -> None:
    eligible_counts = {}
    scored_counts = {}
    for slide_id in processed_slides:
        rows = read_csv(SCORED_DIR / f"{slide_id}.csv")
        scored_counts[slide_id] = len(rows)
        eligible_counts[slide_id] = sum(
            float(row["prob_tumor"]) < PROBABILITY_THRESHOLD for row in rows
        )
    lines = [
        "# Criblage des hard positives Iter9",
        "",
        "Le criblage utilise uniquement les WSI tumorales du split d'entraînement.",
        "Aucune WSI de validation ou de test final n'est lue.",
        "",
        f"- WSI tumorales d'entraînement prévues : {len(train_slides)}",
        f"- WSI traitées : {len(processed_slides)}",
        f"- centres annotés et informatifs scorés : {sum(scored_counts.values())}",
        f"- centres avec probabilité Iter8 < 0,25 : {sum(eligible_counts.values())}",
        f"- candidats retenus pour revue : {len(selected)}",
        "",
        "| Lame | Centres scorés | Centres < 0,25 | Retenus |",
        "|---|---:|---:|---:|",
    ]
    selected_counts = {}
    for row in selected:
        selected_counts[row["slide_id"]] = selected_counts.get(row["slide_id"], 0) + 1
    for slide_id in processed_slides:
        lines.append(
            f"| `{slide_id}` | {scored_counts[slide_id]} | "
            f"{eligible_counts[slide_id]} | {selected_counts.get(slide_id, 0)} |"
        )
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    split_rows = read_csv(SPLIT_CSV)
    train_slides = sorted(
        row["slide_id"]
        for row in split_rows
        if row["split"] == "train" and row["label"] == "tumor"
    )
    if len(train_slides) != 86:
        raise ValueError(f"Expected 86 training tumor WSI, found {len(train_slides)}")
    forbidden = {
        row["slide_id"]
        for row in split_rows
        if row["split"] in {"val", "test_final"}
    }
    if set(train_slides) & forbidden:
        raise ValueError("Train/validation/final-test overlap")

    model = build_model(device)
    SCORED_DIR.mkdir(parents=True, exist_ok=True)
    requested = train_slides[: args.max_slides] if args.max_slides else train_slides
    status("running", device=device, requested_slides=len(requested))
    processed_this_run = 0
    for index, slide_id in enumerate(requested, start=1):
        score_path = SCORED_DIR / f"{slide_id}.csv"
        if score_path.exists() and not args.overwrite:
            print(f"[{index}/{len(requested)}] {slide_id}: already scored", flush=True)
            continue
        rows = score_slide(slide_id, model, device, args.batch_size)
        write_csv(
            score_path,
            rows,
            ["slide_id", "x", "y", "prob_tumor", "nonwhite_ratio"],
        )
        processed_this_run += 1
        eligible = sum(float(row["prob_tumor"]) < PROBABILITY_THRESHOLD for row in rows)
        print(
            f"[{index}/{len(requested)}] {slide_id}: {len(rows)} scored, "
            f"{eligible} below {PROBABILITY_THRESHOLD}",
            flush=True,
        )

    processed_slides = [
        slide_id for slide_id in train_slides if (SCORED_DIR / f"{slide_id}.csv").is_file()
    ]
    selected = build_selection(train_slides)
    write_csv(
        OUTPUT_DIR / "candidates.csv",
        selected,
        [
            "candidate_id", "slide_id", "x", "y", "iter8_prob",
            "nonwhite_ratio", "selection_rank_within_slide", "patch_path",
            "review_image", "site_diagnosis", "dominant_pattern",
            "image_quality", "confidence", "include_as_hard_positive",
            "reviewer", "review_date", "notes",
        ],
    )
    write_summary(train_slides, processed_slides, selected)
    final_state = "complete" if len(processed_slides) == len(train_slides) else "partial"
    status(
        final_state,
        processed_slides=len(processed_slides),
        total_slides=len(train_slides),
        processed_this_run=processed_this_run,
        selected_candidates=len(selected),
    )
    print(f"Mining status: {final_state}; candidates: {len(selected)}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        status("failed", error=repr(exc))
        raise
