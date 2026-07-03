from pathlib import Path
import argparse
import csv
import shutil

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODE_CONFIG = {
    "fp": {
        "default_csv": PROJECT_ROOT / "outputs/iter4_fp_review/review_template.csv",
        "default_sorted_dir": PROJECT_ROOT / "data/review_sorted/iter4_fp_components",
        "image_columns": ["contact_sheet", "patch_path"],
        "include_column": "include_as_hard_negative",
        "title": "False positive / hard negative review",
        "keys": {
            "h": ("other_hard_negative", "yes", "normal", "hard_negative", "Other hard negative"),
            "m": ("macrophage_histiocyte", "yes", "normal", "hard_negative", "Macrophage / histiocyte"),
            "s": ("sinus_histiocytosis", "yes", "normal", "hard_negative", "Sinus histiocytosis"),
            "f": ("fibrosis_stroma_benign", "yes", "normal", "hard_negative", "Benign fibrosis / stroma"),
            "g": ("electrocoagulation_artifact", "yes", "normal", "hard_negative", "Electrocoagulation artifact"),
            "c": ("crush_artifact_benign", "yes", "normal", "hard_negative", "Benign crush artifact"),
            "v": ("vessel_lumen", "yes", "normal", "hard_negative", "Vessel / lumen"),
            "o": ("outside_node_adipose", "yes", "normal", "hard_negative", "Outside node / adipose"),
            "n": ("necrosis_coagulation_benign", "yes", "normal", "hard_negative", "Benign necrosis / coagulation"),
            "a": ("generic_artifact", "yes", "normal", "hard_negative", "Generic artifact"),
            "b": ("benign_not_useful", "no", "normal", "easy_or_not_useful", "Benign but not useful"),
            "u": ("uncertain_review_later", "", "", "uncertain", "Uncertain / review later"),
            "x": ("reject_uninformative", "no", "", "reject", "Reject / uninformative"),
        },
    },
    "hp": {
        "default_csv": PROJECT_ROOT / "outputs/hard_positive_review_iter2/review_template.csv",
        "default_sorted_dir": PROJECT_ROOT / "data/review_sorted/hard_positive_iter2",
        "image_columns": ["patch_path", "contact_sheet"],
        "include_column": "include_as_hard_positive",
        "title": "Hard positive review",
        "keys": {
            "t": ("other_hard_tumor", "yes", "tumor", "hard_positive", "Other hard tumor"),
            "m": ("micrometastasis", "yes", "tumor", "hard_positive", "Micrometastasis"),
            "i": ("isolated_tumor_cells", "yes", "tumor", "hard_positive", "Isolated tumor cells / ITC"),
            "s": ("small_tumor_cluster", "yes", "tumor", "hard_positive", "Small tumor cluster"),
            "c": ("crushed_tumor", "yes", "tumor", "hard_positive", "Crushed tumor"),
            "f": ("tumor_in_fibrosis_stroma", "yes", "tumor", "hard_positive", "Tumor in fibrosis / stroma"),
            "n": ("tumor_in_necrosis_coagulation", "yes", "tumor", "hard_positive", "Tumor in necrosis / coagulation"),
            "a": ("tumor_in_artifact", "yes", "tumor", "hard_positive", "Tumor in artifact"),
            "b": ("metastasis_border_transition", "yes", "tumor", "border_transition", "Metastasis border / transition"),
            "e": ("easy_tumor", "no", "tumor", "easy_or_not_useful", "Easy tumor, not hard"),
            "p": ("partial_or_border_uncertain", "", "", "uncertain", "Partial / border uncertain"),
            "r": ("artifact_or_annotation_noise", "no", "", "reject", "Artifact / annotation noise"),
            "x": ("reject_uninformative", "no", "", "reject", "Reject / uninformative"),
        },
    },
}

CONTROL_KEYS = {
    "right": "skip",
    " ": "skip",
    "left": "back",
    "backspace": "back",
    "q": "quit",
}


def read_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_rows(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def first_existing_path(row, columns):
    for column in columns:
        value = row.get(column, "")
        if not value:
            continue
        path = Path(value)
        if path.exists() and not path.name.startswith("._"):
            return path, column
    return None, None


def row_is_reviewed(row, include_column):
    return bool(row.get("review_category", "").strip()) or bool(row.get(include_column, "").strip())


def unique_destination(dst_dir, src_name):
    dst = dst_dir / src_name
    if not dst.exists():
        return dst

    src = Path(src_name)
    for idx in range(1, 10000):
        candidate = dst_dir / f"{src.stem}_{idx}{src.suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {dst}")


def copy_to_category(image_path, sorted_dir, category, row_label):
    category_dir = sorted_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)

    prefix = row_label.replace("/", "_").replace(" ", "_")
    dst_name = f"{prefix}_{image_path.name}"
    dst = unique_destination(category_dir, dst_name)
    shutil.copy2(image_path, dst)
    return dst


def ensure_columns(fieldnames, include_column):
    fieldnames = list(fieldnames or [])
    for column in [
        "binary_label",
        "morphology_category",
        "difficulty_type",
        "review_category",
        include_column,
        "reviewed_image",
        "sorted_path",
        "notes",
    ]:
        if column not in fieldnames:
            fieldnames.append(column)
    return fieldnames


def row_label(row):
    parts = []
    for key in ["slide_id", "component_id", "candidate_id", "category"]:
        if row.get(key):
            parts.append(f"{key}={row[key]}")
    return "_".join(parts) if parts else "row"


def make_title(row, idx, total, mode_config, image_column, controls):
    metadata = []
    for key in [
        "slide_id",
        "component_id",
        "candidate_id",
        "category",
        "n_patches",
        "max_prob",
        "mean_prob",
        "prob",
        "x",
        "y",
        "top_x",
        "top_y",
    ]:
        value = row.get(key)
        if value not in (None, ""):
            metadata.append(f"{key}: {value}")

    key_help = "  ".join(
        f"[{key}] {label}" for key, (_, _, _, _, label) in mode_config["keys"].items()
    )
    control_help = "[space/right] skip  [left] back  [q] quit"
    return (
        f"{mode_config['title']}  {idx + 1}/{total}\n"
        f"{' | '.join(metadata)}\n"
        f"image: {image_column}\n"
        f"{key_help}\n"
        f"{control_help}\n"
        f"{controls}"
    )


def show_image_and_wait(image_path, title):
    img = mpimg.imread(image_path)
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    ax.imshow(img)
    ax.axis("off")
    ax.set_title(title, fontsize=9)

    key_pressed = {"key": None}

    def on_key(event):
        key_pressed["key"] = event.key
        plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()
    return key_pressed["key"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Keyboard review tool for hard-negative and hard-positive candidates."
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_CONFIG),
        required=True,
        help="Review preset: fp for false positives/hard negatives, hp for hard positives.",
    )
    parser.add_argument("--csv", default=None, help="Review CSV to update in place.")
    parser.add_argument("--sorted-dir", default=None, help="Directory where reviewed images are copied by category.")
    parser.add_argument("--include-reviewed", action="store_true", help="Show rows already reviewed.")
    parser.add_argument("--start", type=int, default=1, help="1-based row index to start from.")
    return parser.parse_args()


def main():
    args = parse_args()
    config = MODE_CONFIG[args.mode]
    csv_path = Path(args.csv) if args.csv else config["default_csv"]
    sorted_dir = Path(args.sorted_dir) if args.sorted_dir else config["default_sorted_dir"]
    include_column = config["include_column"]

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    rows, fieldnames = read_rows(csv_path)
    fieldnames = ensure_columns(fieldnames, include_column)

    if not rows:
        print("Aucune ligne a relire.")
        return

    idx = max(0, args.start - 1)
    reviewed_count = 0

    print("CSV:", csv_path)
    print("Dossier de tri:", sorted_dir)
    print("Touches:")
    for key, (category, include_value, binary_label, difficulty_type, label) in config["keys"].items():
        print(
            f"  {key}: {category} / binary={binary_label!r} / "
            f"difficulty={difficulty_type!r} / include={include_value!r} / {label}"
        )
    print("  space/right: skip")
    print("  left/backspace: back")
    print("  q: quit")

    while idx < len(rows):
        row = rows[idx]
        if row_is_reviewed(row, include_column) and not args.include_reviewed:
            idx += 1
            continue

        image_path, image_column = first_existing_path(row, config["image_columns"])
        if image_path is None:
            print(f"[MISSING] row {idx + 1}: aucune image trouvee")
            row["review_category"] = row.get("review_category", "") or "missing_image"
            write_rows(csv_path, rows, fieldnames)
            idx += 1
            continue

        controls = f"current review: {row.get('review_category', '')} / {row.get(include_column, '')}"
        title = make_title(row, idx, len(rows), config, image_column, controls)
        key = show_image_and_wait(image_path, title)

        if key in CONTROL_KEYS:
            action = CONTROL_KEYS[key]
            if action == "skip":
                print(f"[SKIP] row {idx + 1}")
                idx += 1
            elif action == "back":
                idx = max(0, idx - 1)
                print(f"[BACK] row {idx + 1}")
            elif action == "quit":
                print("Arret demande.")
                break
            continue

        if key not in config["keys"]:
            print(f"[UNKNOWN] touche {key!r}, ligne non modifiee")
            continue

        category, include_value, binary_label, difficulty_type, label = config["keys"][key]
        label_for_file = row_label(row)
        sorted_path = copy_to_category(image_path, sorted_dir, category, label_for_file)

        row["binary_label"] = binary_label
        row["morphology_category"] = category
        row["difficulty_type"] = difficulty_type
        row["review_category"] = category
        row[include_column] = include_value
        row["reviewed_image"] = str(image_path)
        row["sorted_path"] = str(sorted_path)
        write_rows(csv_path, rows, fieldnames)

        reviewed_count += 1
        print(
            f"[{label}] row {idx + 1}: {category}, "
            f"{include_column}={include_value!r}"
        )
        idx += 1

    write_rows(csv_path, rows, fieldnames)
    remaining = sum(
        1
        for row in rows
        if not row_is_reviewed(row, include_column)
    )
    print("\nTermine.")
    print("Nouvelles revues:", reviewed_count)
    print("Restantes non revues:", remaining)
    print("CSV mis a jour:", csv_path)
    print("Images triees:", sorted_dir)


if __name__ == "__main__":
    main()
