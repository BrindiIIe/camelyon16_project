from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPLIT_CSV = ROOT / "outputs" / "splits" / "wsi_split_v1.csv"
OUTPUT_DIR = ROOT / "outputs" / "supervised_comparator_freeze"
REFERENCE_THRESHOLD = 0.5
REFERENCE_COMPONENT_SIZE = 40
MINIMUM_TUMOR_SLIDES_DETECTED = 19

PATCH_THRESHOLDS = [
    0.01,
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
]
COMPONENT_SIZES = [1, 2, 3, 5, 10, 15, 20, 30, 40, 60, 80, 100, 150, 200, 300, 500, 1000]

MODELS = {
    "iter7": {
        "checkpoint": ROOT / "models" / "best_resnet18_patch_iter7.pt",
        "inference_dir": ROOT / "data" / "inference_iter7_val",
    },
    "iter8": {
        "checkpoint": ROOT / "models" / "best_resnet18_patch_iter8.pt",
        "inference_dir": ROOT / "data" / "inference_iter8_val",
    },
}


def load_component_module():
    path = ROOT / "src" / "10_eval_wsi_connected_components.py"
    spec = importlib.util.spec_from_file_location("connected_components", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def true_label(row: dict[str, str]) -> int:
    if row["label"] == "tumor":
        return 1
    if row["label"] == "normal":
        return 0
    raise ValueError(f"Unexpected label for {row['slide_id']}: {row['label']}")


def rule_distance_from_reference(row: dict[str, object]) -> float:
    threshold_distance = abs(float(row["patch_threshold"]) - REFERENCE_THRESHOLD) / REFERENCE_THRESHOLD
    size_distance = abs(int(row["min_component_size"]) - REFERENCE_COMPONENT_SIZE) / REFERENCE_COMPONENT_SIZE
    return threshold_distance + size_distance


def main() -> None:
    cc = load_component_module()
    split_rows = read_csv(SPLIT_CSV)
    validation_rows = [row for row in split_rows if row["split"] == "val"]
    test_rows = [row for row in split_rows if row["split"] == "test_final"]
    if len(validation_rows) != 48:
        raise ValueError(f"Expected 48 validation slides, found {len(validation_rows)}")
    if sum(true_label(row) for row in validation_rows) != 19:
        raise ValueError("Expected 19 tumor validation slides")
    if len(test_rows) != 125:
        raise ValueError(f"Expected 125 untouched final-test slides, found {len(test_rows)}")

    validation_grid: list[dict[str, object]] = []
    per_slide_rows: list[dict[str, object]] = []

    for model_name, model in MODELS.items():
        inference_dir = Path(model["inference_dir"])
        checkpoint = Path(model["checkpoint"])
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)

        slide_data = {}
        labels = {}
        for split_row in validation_rows:
            slide_id = split_row["slide_id"]
            probability_csv = inference_dir / f"{slide_id}_probs.csv"
            if not probability_csv.is_file():
                raise FileNotFoundError(probability_csv)
            slide_data[slide_id] = cc.read_probs(probability_csv)
            labels[slide_id] = true_label(split_row)

        threshold_results: dict[tuple[str, float], dict[str, object]] = {}
        for threshold in PATCH_THRESHOLDS:
            for slide_id, probabilities in slide_data.items():
                metrics = cc.evaluate_slide(
                    probabilities,
                    patch_threshold=threshold,
                    min_component_size=1,
                    stride=128,
                )
                threshold_results[(slide_id, threshold)] = metrics

        for threshold in PATCH_THRESHOLDS:
            for component_size in COMPONENT_SIZES:
                prediction_rows = []
                for slide_id in sorted(slide_data):
                    metrics = threshold_results[(slide_id, threshold)]
                    prediction = int(int(metrics["largest_component"]) >= component_size)
                    prediction_row = {
                        "model": model_name,
                        "slide_id": slide_id,
                        "true_label": labels[slide_id],
                        "patch_threshold": threshold,
                        "min_component_size": component_size,
                        "max_prob": metrics["max_prob"],
                        "positive_patches": metrics["positive_patches"],
                        "largest_component": metrics["largest_component"],
                        "pred_label": prediction,
                    }
                    prediction_rows.append(prediction_row)
                    per_slide_rows.append(prediction_row)

                summary = cc.compute_summary(prediction_rows)
                validation_grid.append(
                    {
                        "model": model_name,
                        "patch_threshold": threshold,
                        "min_component_size": component_size,
                        "n_slides": len(prediction_rows),
                        **summary,
                    }
                )

    eligible = [row for row in validation_grid if int(row["tp"]) >= MINIMUM_TUMOR_SLIDES_DETECTED]
    if not eligible:
        raise RuntimeError("No candidate meets the sensitivity constraint")

    best_specificity = max(float(row["specificity"]) for row in eligible)
    specificity_ties = [row for row in eligible if float(row["specificity"]) == best_specificity]
    best_sensitivity = max(float(row["sensitivity"]) for row in specificity_ties)
    performance_ties = [row for row in specificity_ties if float(row["sensitivity"]) == best_sensitivity]
    selected = min(
        performance_ties,
        key=lambda row: (
            rule_distance_from_reference(row),
            -float(row["f1"]),
            str(row["model"]),
        ),
    )

    selected_model = str(selected["model"])
    selected_checkpoint = Path(MODELS[selected_model]["checkpoint"])
    decision = {
        "status": "frozen_before_final_test",
        "selection_dataset": "wsi_split_v1:val",
        "validation_slides": len(validation_rows),
        "validation_tumor_slides": 19,
        "validation_normal_slides": 29,
        "final_test_slides_confirmed_untouched": len(test_rows),
        "primary_criterion": (
            "Maximize specificity among candidate model/rule pairs detecting at least "
            "19 of 19 tumor validation slides (100% sensitivity)."
        ),
        "tie_breaker": (
            "Among performance-equivalent rules, choose the rule closest to the prior "
            "reference threshold 0.5 and component size 40."
        ),
        "model": selected_model,
        "checkpoint": str(selected_checkpoint.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_sha256": sha256(selected_checkpoint),
        "patch_threshold": selected["patch_threshold"],
        "min_component_size": selected["min_component_size"],
        "stride": 128,
        "validation_metrics": {
            key: selected[key]
            for key in ("sensitivity", "specificity", "precision", "f1", "accuracy", "tp", "fp", "fn", "tn")
        },
        "grid": {
            "patch_thresholds": PATCH_THRESHOLDS,
            "min_component_sizes": COMPONENT_SIZES,
            "models": list(MODELS),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "validation_grid.csv", validation_grid)
    write_csv(OUTPUT_DIR / "validation_per_slide.csv", per_slide_rows)
    (OUTPUT_DIR / "freeze_decision.json").write_text(
        json.dumps(decision, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    metrics = decision["validation_metrics"]
    component_unit = "patch" if int(decision["min_component_size"]) == 1 else "patches"
    markdown = f"""# Gel du comparateur supervisé

## Décision

Le comparateur supervisé est figé avant toute inférence sur le jeu
`test_final`.

- modèle : `{decision['model']}` ;
- checkpoint : `{decision['checkpoint']}` ;
- empreinte SHA-256 : `{decision['checkpoint_sha256']}` ;
- seuil patch : {decision['patch_threshold']} ;
- taille minimale de composante : {decision['min_component_size']} {component_unit} ;
- stride : 128 pixels.

## Critère défini avant le test final

La règle maximise la spécificité parmi les couples modèle/règle détectant les
19 lames tumorales de validation, soit une sensibilité de 100 %. En cas
d'égalité de performance, la règle la plus proche du point de référence
historique 0,5/40 est retenue.

## Performance de validation du choix figé

| Sensibilité | Spécificité | Précision | F1 | Exactitude | VP | FP | FN | VN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| {metrics['sensitivity']:.3f} | {metrics['specificity']:.3f} | {metrics['precision']:.3f} | {metrics['f1']:.3f} | {metrics['accuracy']:.3f} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} | {metrics['tn']} |

La grille commune comprend {len(PATCH_THRESHOLDS)} seuils et
{len(COMPONENT_SIZES)} tailles de composante pour `iter7` et `iter8`. Les 125
lames de `test_final` n'ont pas été lues pour prendre cette décision. Le
fichier `freeze_decision.json` constitue la spécification exécutable de
l'évaluation finale.
"""
    (OUTPUT_DIR / "README.md").write_text(markdown, encoding="utf-8")
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
