from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "outputs" / "supervised_comparator_freeze"
DECISION_PATH = FREEZE_DIR / "freeze_decision.json"
SPLIT_PATH = ROOT / "outputs" / "splits" / "wsi_split_v1.csv"
QUEUE_PATH = ROOT / "outputs" / "inference_queues" / "frozen_supervised_test_final_queue.csv"
INFERENCE_DIR = ROOT / "data" / "inference_supervised_test_final"
RESULT_DIR = ROOT / "outputs" / "supervised_comparator_final_test"
STATUS_PATH = RESULT_DIR / "status.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the once-only final test with the frozen supervised comparator."
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--max-slides", type=int, default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--progress-every", type=int, default=10)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_status(state: str, **details: object) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": state,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        **details,
    }
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_component_module():
    path = ROOT / "src" / "10_eval_wsi_connected_components.py"
    spec = importlib.util.spec_from_file_location("connected_components", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_and_validate_decision() -> dict[str, object]:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    if decision.get("status") != "frozen_before_final_test":
        raise ValueError("The supervised comparator is not frozen")
    if float(decision["validation_metrics"]["sensitivity"]) != 1.0:
        raise ValueError("The frozen comparator does not meet 100% validation sensitivity")
    checkpoint = ROOT / str(decision["checkpoint"])
    if sha256(checkpoint) != decision["checkpoint_sha256"]:
        raise ValueError("Checkpoint SHA-256 does not match the frozen decision")
    return decision


def prepare_queue(decision: dict[str, object]) -> list[dict[str, str]]:
    split_rows = read_csv(SPLIT_PATH)
    test_rows = sorted(
        (row for row in split_rows if row["split"] == "test_final"),
        key=lambda row: int(row["slide_id"].split("_", 1)[1]),
    )
    if len(test_rows) != 125:
        raise ValueError(f"Expected 125 final-test slides, found {len(test_rows)}")
    if any(row["used_for_hard_mining"] == "yes" for row in test_rows):
        raise ValueError("A final-test slide was used for hard mining")

    if QUEUE_PATH.exists():
        queue_rows = read_csv(QUEUE_PATH)
        if [row["slide_id"] for row in queue_rows] != [row["slide_id"] for row in test_rows]:
            raise ValueError("Existing final-test queue does not match the frozen split")
        return queue_rows

    created_at = datetime.now().isoformat(timespec="seconds")
    queue_rows = []
    for index, row in enumerate(test_rows, start=1):
        queue_rows.append(
            {
                "queue_index": index,
                "slide_id": row["slide_id"],
                "slide_filename": f"{row['slide_id']}.tif",
                "label": row["label"],
                "split": "test_final",
                "experiment": str(decision["model"]),
                "purpose": "once_only_frozen_final_test",
                "wsi_path": row["wsi_path"],
                "annotation_path": row["annotation_path"],
                "used_for_hard_mining": row["used_for_hard_mining"],
                "hard_mining_role": row["hard_mining_role"],
                "status": "pending",
                "attempts": 0,
                "created_at": created_at,
                "started_at": "",
                "finished_at": "",
                "seconds": "",
                "n_patches": "",
                "output_csv": "",
                "notes": "",
            }
        )
    write_csv(QUEUE_PATH, queue_rows)
    return read_csv(QUEUE_PATH)


def evaluate_complete_test(decision: dict[str, object], queue_rows: list[dict[str, str]]) -> None:
    if any(row["status"] != "done" for row in queue_rows):
        raise ValueError("Final-test evaluation requested before all inference rows were complete")

    cc = load_component_module()
    threshold = float(decision["patch_threshold"])
    component_size = int(decision["min_component_size"])
    stride = int(decision["stride"])
    per_slide = []
    for row in queue_rows:
        probability_csv = INFERENCE_DIR / f"{row['slide_id']}_probs.csv"
        probabilities = cc.read_probs(probability_csv)
        metrics = cc.evaluate_slide(probabilities, threshold, component_size, stride)
        per_slide.append(
            {
                "slide_id": row["slide_id"],
                "true_label": 1 if row["label"] == "tumor" else 0,
                "pred_label": metrics["pred_label"],
                "max_prob": metrics["max_prob"],
                "positive_patches": metrics["positive_patches"],
                "largest_component": metrics["largest_component"],
            }
        )

    summary = cc.compute_summary(per_slide)
    write_csv(RESULT_DIR / "per_slide.csv", per_slide)
    payload = {
        "status": "complete_no_further_tuning",
        "model": decision["model"],
        "checkpoint": decision["checkpoint"],
        "checkpoint_sha256": decision["checkpoint_sha256"],
        "patch_threshold": threshold,
        "min_component_size": component_size,
        "stride": stride,
        "n_slides": len(per_slide),
        **summary,
    }
    (RESULT_DIR / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown = f"""# Évaluation finale du comparateur supervisé

Le checkpoint et la règle ont été figés sur la validation avant cette
évaluation. Aucun réglage supplémentaire n'est autorisé à partir de ces
résultats.

| Lames | Sensibilité | Spécificité | Précision | F1 | Exactitude | VP | FP | FN | VN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| {len(per_slide)} | {summary['sensitivity']:.3f} | {summary['specificity']:.3f} | {summary['precision']:.3f} | {summary['f1']:.3f} | {summary['accuracy']:.3f} | {summary['tp']} | {summary['fp']} | {summary['fn']} | {summary['tn']} |
"""
    (RESULT_DIR / "README.md").write_text(markdown, encoding="utf-8")
    write_status("complete", completed_slides=len(queue_rows), summary=payload)


def main() -> None:
    args = parse_args()
    decision = load_and_validate_decision()
    queue_rows = prepare_queue(decision)
    completed = sum(row["status"] == "done" for row in queue_rows)
    write_status(
        "prepared" if args.prepare_only else "inference_starting",
        completed_slides=completed,
        total_slides=len(queue_rows),
        model=decision["model"],
        patch_threshold=decision["patch_threshold"],
        min_component_size=decision["min_component_size"],
    )
    if args.prepare_only:
        print(f"Prepared final-test queue with {len(queue_rows)} slides: {QUEUE_PATH}")
        return

    command = [
        sys.executable,
        "-u",
        str(ROOT / "src" / "21_run_inference_queue.py"),
        "--queue-csv",
        str(QUEUE_PATH),
        "--model-path",
        str(ROOT / str(decision["checkpoint"])),
        "--output-dir",
        str(INFERENCE_DIR),
        "--device",
        args.device,
        "--stride",
        str(decision["stride"]),
        "--batch-size",
        str(args.batch_size),
        "--progress-every",
        str(args.progress_every),
        "--resume",
    ]
    if args.max_slides is not None:
        command.extend(["--max-slides", str(args.max_slides)])
    subprocess.run(command, cwd=ROOT, check=True)

    queue_rows = read_csv(QUEUE_PATH)
    completed = sum(row["status"] == "done" for row in queue_rows)
    if completed == len(queue_rows):
        evaluate_complete_test(decision, queue_rows)
        print(f"Final test complete: {RESULT_DIR}")
    else:
        write_status(
            "inference_in_progress",
            completed_slides=completed,
            total_slides=len(queue_rows),
            remaining_slides=len(queue_rows) - completed,
        )
        print(f"Final-test inference progress: {completed}/{len(queue_rows)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_status("failed", error=repr(exc))
        raise
