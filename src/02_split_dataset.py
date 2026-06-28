from pathlib import Path
import shutil
import random
from collections import Counter, defaultdict

DATA_DIR = Path("../data/patches/train")
OUTPUT_DIR = Path("../data/patches_base")

MAX_NORMAL_PER_SLIDE = 80
MAX_TUMOR_PER_SLIDE = 200

TRAIN_SLIDES = {
    "tumor_001", "tumor_003", "tumor_004", "tumor_005",
    "normal_001", "normal_002", "normal_003", "normal_004", "normal_005",
}

VAL_SLIDES = {
    "tumor_007",
    "normal_006", "normal_007",
}

TEST_SLIDES = {
    "tumor_006",
    "normal_008", "normal_009",
}

EXCLUDED_SLIDES = {
    "tumor_002", "tumor_008", "tumor_009", "tumor_010",
    "normal_010",
}


def remove_mac_hidden_files(root_dir):
    root_dir = Path(root_dir)
    for path in root_dir.rglob("._*"):
        path.unlink(missing_ok=True)


def get_slide_name(filename):
    name = Path(filename).stem  # enlève .png
    parts = name.split("_")

    # attend des noms du style:
    # tumor_001_tumor_x_y.png
    # normal_003_normal_x_y.png
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"

    return None


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

    available_counts = {
        "normal": Counter(),
        "tumor": Counter(),
    }

    selected_counts = {
        "train": {"normal": Counter(), "tumor": Counter()},
        "val": {"normal": Counter(), "tumor": Counter()},
        "test": {"normal": Counter(), "tumor": Counter()},
    }

    unknown_files = []
    unknown_slides = Counter()

    all_known_slides = TRAIN_SLIDES | VAL_SLIDES | TEST_SLIDES

    # Audit global avant split
    for label in ["normal", "tumor"]:
        folder = DATA_DIR / label
        all_patches = [p for p in folder.glob("*.png") if not p.name.startswith("._")]

        print(f"\n--- Audit dossier {folder} ---")
        print(f"Total fichiers .png trouvés : {len(all_patches)}")

        for patch in all_patches:
            slide_name = get_slide_name(patch.name)

            if slide_name is None:
                unknown_files.append(patch.name)
                continue

            available_counts[label][slide_name] += 1

            if slide_name not in all_known_slides:
                unknown_slides[slide_name] += 1

        print(f"Répartition par slide ({label}) :")
        for slide, n in sorted(available_counts[label].items()):
            marker = ""
            if slide not in all_known_slides:
                marker = "  <-- slide non assignée"
            print(f"  {slide}: {n}{marker}")

    if unknown_files:
        print("\nFichiers non parsés correctement :")
        for name in unknown_files[:20]:
            print(" ", name)
        if len(unknown_files) > 20:
            print(f"  ... +{len(unknown_files)-20} autres")

    if unknown_slides:
        print("\nSlides trouvées mais absentes de TRAIN/VAL/TEST :")
        for slide, n in sorted(unknown_slides.items()):
            print(f"  {slide}: {n}")

    # Split
    for slide_name in all_known_slides:
        split = get_split_for_slide(slide_name)

        for label in ["normal", "tumor"]:
            folder = DATA_DIR / label

            matching_patches = [
                patch for patch in folder.glob("*.png")
                if not patch.name.startswith("._") and get_slide_name(patch.name) == slide_name
            ]

            before = len(matching_patches)

            if label == "normal":
                max_count = MAX_NORMAL_PER_SLIDE
            else:
                max_count = MAX_TUMOR_PER_SLIDE

            if len(matching_patches) > max_count:
                matching_patches = random.sample(matching_patches, max_count)

            after = len(matching_patches)
            selected_counts[split][label][slide_name] = after

            print(f"{split.upper()} | {label:6s} | {slide_name:10s} | dispo={before:4d} -> gardés={after:4d}")

            for patch in matching_patches:
                copy_patch(patch, split, label)
                counts[split][label] += 1

    print("\nRésumé final :")
    for split in ["train", "val", "test"]:
        print(split.upper(), counts[split])


if __name__ == "__main__":
    main()