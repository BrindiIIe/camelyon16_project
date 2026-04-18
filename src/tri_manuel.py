from pathlib import Path
import shutil
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

SRC_DIR = Path("../data/hard_negatives")
KEEP_DIR = SRC_DIR / "keep"
REJECT_DIR = SRC_DIR / "reject"
MAYBE_DIR = SRC_DIR / "maybe"

KEEP_DIR.mkdir(exist_ok=True)
REJECT_DIR.mkdir(exist_ok=True)
MAYBE_DIR.mkdir(exist_ok=True)

image_paths = sorted([
    p for p in SRC_DIR.glob("*.png")
    if p.is_file() and not p.name.startswith("._")
])

print(f"{len(image_paths)} patches à trier")

for i, img_path in enumerate(image_paths, 1):
    img = mpimg.imread(img_path)

    plt.figure(figsize=(6, 6))
    plt.imshow(img)
    plt.title(f"{i}/{len(image_paths)}\n{img_path.name}\n[k] keep   [r] reject   [m] maybe   [q] quit")
    plt.axis("off")
    plt.show(block=False)

    choice = input("Choix [k/r/m/q] : ").strip().lower()
    plt.close()

    if choice == "q":
        print("Arrêt du tri.")
        break
    elif choice == "k":
        dest = KEEP_DIR / img_path.name
    elif choice == "r":
        dest = REJECT_DIR / img_path.name
    elif choice == "m":
        dest = MAYBE_DIR / img_path.name
    else:
        print("Choix invalide, patch laissé en place.")
        continue

    shutil.move(str(img_path), str(dest))
    print(f"Déplacé vers : {dest}")