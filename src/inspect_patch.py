# inspect_patches.py

from pathlib import Path
import random
import matplotlib.pyplot as plt
from PIL import Image

TUMOR_DIR = Path("../data/patches/train/tumor")
NORMAL_DIR = Path("../data/patches/train/normal")


def show_random_patches(folder, title, n=12):

    files = [p for p in folder.glob("*.png") if not p.name.startswith("._")]
    samples = random.sample(files, min(n, len(files)))

    fig, axes = plt.subplots(3, 4, figsize=(10, 8))

    for ax, file in zip(axes.flatten(), samples):
        img = Image.open(file)
        ax.imshow(img)
        ax.set_title(file.name[:20])
        ax.axis("off")

    plt.suptitle(title)
    plt.tight_layout()
    plt.show()


show_random_patches(TUMOR_DIR, "Tumor patches")
show_random_patches(NORMAL_DIR, "Normal patches")