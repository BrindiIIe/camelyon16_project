from pathlib import Path
import shutil
import random

DATA_DIR = Path("../data/patches/train")
OUTPUT_DIR = Path("../data/patches_split")

MAX_NORMAL_PER_SLIDE = 500
MAX_TUMOR_PER_SLIDE = 500

TRAIN_SLIDES = {
    "tumor_001",
    "tumor_008",
    "tumor_003",
    "tumor_005",
    "tumor_006",
    "tumor_004",
}

VAL_SLIDES = {
    "tumor_007",
    "tumor_002",
}

TEST_SLIDES = {
    "tumor_009",
}

def remove_mac_hidden_files(root_dir):
    root_dir = Path(root_dir)
    for path in root_dir.rglob("._*"):
        path.unlink(missing_ok=True)


def get_slide_name(filename):
    return filename.split("_tumor_")[0].split("_normal_")[0]


def get_split_for_slide(slide_name):
    if slide_name in TRAIN_SLIDES:
        return "train"
    if slide_name in VAL_SLIDES:
        return "val"
    if slide_name in TEST_SLIDES:
        return "test"
    return None


def copy_patch(patch_path, split, label):
    dest = OUTPUT_DIR / split / label
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(patch_path, dest / patch_path.name)


def main():
    random.seed(42)
    remove_mac_hidden_files(DATA_DIR)
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    print("TRAIN_SLIDES =", TRAIN_SLIDES)
    print("VAL_SLIDES =", VAL_SLIDES)
    print("TEST_SLIDES =", TEST_SLIDES)

    counts = {
        "train": {"normal": 0, "tumor": 0},
        "val": {"normal": 0, "tumor": 0},
        "test": {"normal": 0, "tumor": 0},
    }

    for slide_name in TRAIN_SLIDES | VAL_SLIDES | TEST_SLIDES:
        split = get_split_for_slide(slide_name)

        for label in ["normal", "tumor"]:
            folder = DATA_DIR / label

            matching_patches = [
                patch for patch in folder.glob("*.png")
                if not patch.name.startswith("._") and get_slide_name(patch.name) == slide_name
            ]

            if label == "normal":
                max_count = MAX_NORMAL_PER_SLIDE
            else:
                max_count = MAX_TUMOR_PER_SLIDE

            if len(matching_patches) > max_count:
                matching_patches = random.sample(matching_patches, max_count)

            for patch in matching_patches:
                copy_patch(patch, split, label)
                counts[split][label] += 1

    print("\nRésumé:")
    for split in ["train", "val", "test"]:
        print(split.upper(), counts[split])

if __name__ == "__main__":
    main()