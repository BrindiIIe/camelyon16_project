import os
import random
from collections import defaultdict
from pathlib import Path

# =========================
# CONFIG
# =========================

TUMOR_DIR = "../data/patches_split/train/tumor"
NORMAL_DIR = "../data/patches_split/train/normal"
HARD_NEG_DIR = "../data/hard_negatives/keep"

OUTPUT_CSV = "../data/train_dataset.csv"

# Taille finale cible de la classe normal
# Si None -> prend le même nombre que tumor
TARGET_NORMAL = None

# Proportion de hard negatives dans la classe normal finale
# Exemple 0.7 = 70% hard negatives, 30% normal classiques
HARD_RATIO = 0.7

# Limite max de hard negatives gardés par slide
MAX_HARD_PER_SLIDE = 25

# Seed pour reproductibilité
SEED = 42


# =========================
# UTILS
# =========================

def set_seed(seed=42):
    random.seed(seed)


def is_image_file(filename: str) -> bool:
    filename = filename.lower()
    if filename.startswith("._"):
        return False
    return filename.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))


def list_image_paths(folder):
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"Dossier introuvable: {folder}")
    return sorted(
        [str(p) for p in folder.iterdir() if p.is_file() and is_image_file(p.name)]
    )


def get_slide_id(filepath: str) -> str:
    """
    Suppose des noms comme :
      tumor_001_tumor_71808_123520.png
      normal_002_hard_456_789.png
      normal_015_normal_123_456.png

    -> renvoie tumor_001 ou normal_002 etc.
    """
    name = Path(filepath).stem
    parts = name.split("_")
    if len(parts) < 2:
        return name
    return "_".join(parts[:2])


def group_by_slide(paths):
    d = defaultdict(list)
    for p in paths:
        slide_id = get_slide_id(p)
        d[slide_id].append(p)
    return d


def sample_hard_negatives(hard_paths, max_per_slide, target_count):
    """
    Limite d'abord par slide, puis échantillonne au total.
    """
    by_slide = group_by_slide(hard_paths)

    filtered = []
    for slide_id, paths in by_slide.items():
        random.shuffle(paths)
        filtered.extend(paths[:max_per_slide])

    random.shuffle(filtered)

    if target_count is None:
        return filtered

    return filtered[:min(target_count, len(filtered))]


def sample_normal_paths(normal_paths, target_count):
    random.shuffle(normal_paths)
    return normal_paths[:min(target_count, len(normal_paths))]


def summarize_slide_distribution(paths, title):
    by_slide = group_by_slide(paths)
    print(f"\n{title}")
    print(f"  total patches: {len(paths)}")
    print(f"  total slides : {len(by_slide)}")
    counts = sorted([len(v) for v in by_slide.values()], reverse=True)
    if counts:
        print(f"  max patches/slide: {counts[0]}")
        print(f"  min patches/slide: {counts[-1]}")
        print(f"  median approx    : {counts[len(counts)//2]}")
    else:
        print("  vide")


def save_csv(samples, output_csv):
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv, "w", encoding="utf-8") as f:
        f.write("path,label,source,slide_id\n")
        for path, label, source, slide_id in samples:
            f.write(f"{path},{label},{source},{slide_id}\n")


# =========================
# MAIN
# =========================

def build_train_dataset(
    tumor_dir,
    normal_dir,
    hard_neg_dir,
    output_csv,
    target_normal=None,
    hard_ratio=0.7,
    max_hard_per_slide=25,
    seed=42,
):
    set_seed(seed)

    tumor_paths = list_image_paths(tumor_dir)
    normal_paths = list_image_paths(normal_dir)
    hard_paths = list_image_paths(hard_neg_dir)

    if len(tumor_paths) == 0:
        raise ValueError("Aucun patch tumor trouvé.")
    if len(normal_paths) == 0:
        print("Attention: aucun patch normal classique trouvé.")
    if len(hard_paths) == 0:
        print("Attention: aucun hard negative trouvé.")

    n_tumor = len(tumor_paths)

    if target_normal is None:
        target_normal = n_tumor

    if not (0 <= hard_ratio <= 1):
        raise ValueError("hard_ratio doit être entre 0 et 1.")

    target_hard = int(round(target_normal * hard_ratio))
    target_easy = target_normal - target_hard

    selected_hard = sample_hard_negatives(
        hard_paths,
        max_per_slide=max_hard_per_slide,
        target_count=target_hard
    )

    # Si pas assez de hard negatives après filtrage, on compense avec des normaux classiques
    actual_hard = len(selected_hard)
    missing_hard = target_hard - actual_hard
    target_easy = target_easy + max(0, missing_hard)

    selected_normal = sample_normal_paths(normal_paths, target_easy)

    actual_easy = len(selected_normal)

    final_normal_count = actual_hard + actual_easy

    samples = []

    for p in tumor_paths:
        samples.append((p, 1, "tumor", get_slide_id(p)))

    for p in selected_hard:
        samples.append((p, 0, "hard_negative", get_slide_id(p)))

    for p in selected_normal:
        samples.append((p, 0, "normal", get_slide_id(p)))

    random.shuffle(samples)

    # Résumé console
    print("\n====================")
    print("BUILD TRAIN DATASET")
    print("====================")
    print(f"Tumor disponibles         : {len(tumor_paths)}")
    print(f"Normal classiques dispo   : {len(normal_paths)}")
    print(f"Hard negatives dispo      : {len(hard_paths)}")
    print()
    print(f"Target normal total       : {target_normal}")
    print(f"Target hard negatives     : {target_hard}")
    print(f"Target normal classiques  : {target_normal - target_hard}")
    print()
    print(f"Hard negatives retenus    : {actual_hard}")
    print(f"Normal classiques retenus : {actual_easy}")
    print(f"Normal final              : {final_normal_count}")
    print(f"Tumor final               : {len(tumor_paths)}")
    print(f"Total final dataset       : {len(samples)}")

    summarize_slide_distribution(selected_hard, "Répartition hard negatives retenus")
    summarize_slide_distribution(selected_normal, "Répartition normal classiques retenus")
    summarize_slide_distribution(tumor_paths, "Répartition tumor")

    save_csv(samples, output_csv)
    print(f"\nCSV sauvegardé dans : {output_csv}")


if __name__ == "__main__":
    build_train_dataset(
        tumor_dir=TUMOR_DIR,
        normal_dir=NORMAL_DIR,
        hard_neg_dir=HARD_NEG_DIR,
        output_csv=OUTPUT_CSV,
        target_normal=TARGET_NORMAL,
        hard_ratio=HARD_RATIO,
        max_hard_per_slide=MAX_HARD_PER_SLIDE,
        seed=SEED,
    )