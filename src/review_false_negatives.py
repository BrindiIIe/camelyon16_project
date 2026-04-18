import shutil
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

SOURCE_DIR = Path("../data/review/false_negatives_val_tumor")
KEEP_DIR = Path("../data/review/fn_tumor_keep")
REJECT_DIR = Path("../data/review/fn_tumor_reject")
HARD_DIR = Path("../data/review/fn_tumor_hard")

VALID_EXT = {".png", ".jpg", ".jpeg"}

KEEP_DIR.mkdir(parents=True, exist_ok=True)
REJECT_DIR.mkdir(parents=True, exist_ok=True)
HARD_DIR.mkdir(parents=True, exist_ok=True)


def get_images(folder: Path):
    return sorted(
        [
            p for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() in VALID_EXT
            and not p.name.startswith("._")  # 🔥 IMPORTANT
        ]
    )

def move_file(src: Path, dst_dir: Path):
    dst = dst_dir / src.name
    if dst.exists():
        stem = src.stem
        suffix = src.suffix
        i = 1
        while True:
            candidate = dst_dir / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                dst = candidate
                break
            i += 1
    shutil.move(str(src), str(dst))


def review_images():
    images = get_images(SOURCE_DIR)

    if not images:
        print("Aucune image à relire.")
        return

    i = 0

    while i < len(images):
        img_path = images[i]

        if not img_path.exists():
            i += 1
            continue

        img = mpimg.imread(img_path)

        plt.figure(figsize=(8, 8))
        plt.imshow(img)
        plt.axis("off")
        plt.title(
            f"{i+1}/{len(images)}\n{img_path.name}\n"
            "[k] keep  [h] hard  [d] reject  [q] quit"
        )

        key_pressed = {"key": None}

        def on_key(event):
            key_pressed["key"] = event.key
            plt.close()

        plt.gcf().canvas.mpl_connect("key_press_event", on_key)
        plt.show()

        key = key_pressed["key"]

        if key == "k":
            move_file(img_path, KEEP_DIR)
            print(f"[KEEP]   {img_path.name}")
            i += 1
        elif key == "h":
            move_file(img_path, HARD_DIR)
            print(f"[HARD]   {img_path.name}")
            i += 1
        elif key == "d":
            move_file(img_path, REJECT_DIR)
            print(f"[REJECT] {img_path.name}")
            i += 1
        elif key == "q":
            print("Arrêt demandé.")
            break
        else:
            print(f"[SKIP]   {img_path.name} (touche non reconnue)")

    print("\nTerminé.")
    print(f"Restants dans source : {len(get_images(SOURCE_DIR))}")
    print(f"Gardés : {len(get_images(KEEP_DIR))}")
    print(f"Hard : {len(get_images(HARD_DIR))}")
    print(f"Rejetés : {len(get_images(REJECT_DIR))}")


if __name__ == "__main__":
    review_images()