from pathlib import Path
import argparse
import csv
import importlib.util
import time
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "models/best_resnet18_patch_iter2.pt"
DEFAULT_WSI_DIR = PROJECT_ROOT / "data/wsi"


def load_infer_module():
    module_path = PROJECT_ROOT / "src/05_infer_wsi.py"
    spec = importlib.util.spec_from_file_location("infer_wsi", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_queue(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_queue(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def count_csv_rows(path):
    if not path.exists():
        return 0
    with open(path, "r", newline="", encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run WSI inference from a resumable queue CSV."
    )
    parser.add_argument("--queue-csv", required=True)
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL))
    parser.add_argument("--wsi-dir", default=str(DEFAULT_WSI_DIR))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--max-slides", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true", default=True)
    return parser.parse_args()


def main():
    args = parse_args()
    queue_path = Path(args.queue_csv)
    model_path = Path(args.model_path)
    wsi_dir = Path(args.wsi_dir)
    output_dir = Path(args.output_dir)

    rows, fieldnames = read_queue(queue_path)
    infer = load_infer_module()
    device = infer.resolve_device(args.device)
    model = infer.build_model(model_path, device)

    completed_this_run = 0
    for row in rows:
        if args.max_slides is not None and completed_this_run >= args.max_slides:
            break
        if row.get("status") == "done" and not args.overwrite:
            continue

        slide_filename = row["slide_filename"]
        wsi_path = wsi_dir / slide_filename
        output_csv = output_dir / f"{Path(slide_filename).stem}_probs.csv"

        row["attempts"] = str(int(row.get("attempts") or 0) + 1)
        row["started_at"] = datetime.now().isoformat(timespec="seconds")
        row["status"] = "running"
        row["output_csv"] = str(output_csv)
        write_queue(queue_path, rows, fieldnames)

        start = time.time()
        try:
            if not wsi_path.exists():
                raise FileNotFoundError(wsi_path)

            infer.infer_one_slide(
                wsi_path=wsi_path,
                model=model,
                output_dir=output_dir,
                device=device,
                stride=args.stride,
                batch_size=args.batch_size,
                overwrite=args.overwrite,
                resume=args.resume,
                progress_every=args.progress_every,
            )

            elapsed = time.time() - start
            row["status"] = "done"
            row["finished_at"] = datetime.now().isoformat(timespec="seconds")
            row["seconds"] = f"{elapsed:.1f}"
            row["n_patches"] = str(count_csv_rows(output_csv))
            row["notes"] = ""
            completed_this_run += 1
        except Exception as exc:
            elapsed = time.time() - start
            row["status"] = "failed"
            row["finished_at"] = datetime.now().isoformat(timespec="seconds")
            row["seconds"] = f"{elapsed:.1f}"
            row["notes"] = repr(exc)
            write_queue(queue_path, rows, fieldnames)
            raise
        finally:
            write_queue(queue_path, rows, fieldnames)

    print("Queue updated:", queue_path)
    print("Slides completed this run:", completed_this_run)


if __name__ == "__main__":
    main()
