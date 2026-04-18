import csv
import random
from pathlib import Path

NORMAL_DIR = Path("../data/patches_split/train/normal_keep")
TUMOR_DIR = Path("../data/patches_split/train/tumor_keep")
OUTPUT_CSV = Path("../data/train_dataset.csv")

VALID_EXT = {".png", ".jpg", ".jpeg"}


def list_images(folder: Path):
    return sorted(
        str(p.resolve())
        for p in folder.rglob("*")
        if p.is_file()
        and p.suffix.lower() in VALID_EXT
        and not p.name.startswith("._")
    )


def main():
    normal_paths = list_images(NORMAL_DIR)
    tumor_paths = list_images(TUMOR_DIR)

    rows = []
    rows += [{"path": p, "label": 0} for p in normal_paths]
    rows += [{"path": p, "label": 1} for p in tumor_paths]

    random.seed(42)
    random.shuffle(rows)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV écrit : {OUTPUT_CSV}")
    print(f"normal_keep: {len(normal_paths)}")
    print(f"tumor:       {len(tumor_paths)}")
    print(f"total:       {len(rows)}")


if __name__ == "__main__":
    main()