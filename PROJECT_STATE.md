# CAMELYON16 Metastasis Detection Project State

Last updated: 2026-06-29

## Project Goal

This thesis project builds a pipeline for detecting lymph-node metastases on
CAMELYON16 whole-slide images (WSI). The current implementation uses a
patch-level ResNet18 classifier, WSI-level inference, heatmap visualization,
and WSI-level decision rules based on connected components of positive patches.

The current most useful model is `iter2`.

## Environment

Use the project virtual environment:

```bash
myenv311/bin/python ...
```

The plain system `python3` may not have `torch` installed and may also try to
write Python cache files outside the workspace.

## Current Data Layout

- WSI: `data/wsi/`
- Annotations: `data/annotations/`
- Base patch split: `data/patches_base/`
- Iterative training sets:
  - `data/patches_iter1/`
  - `data/patches_iter2/`
  - `data/patches_iter3/`
- Iter2 WSI inference outputs: `data/inference_iter2/`
- Iter2 heatmaps: `data/inference_iter2/heatmaps/`

The 20 WSI currently used for WSI-level evaluation are:

- `tumor_001` to `tumor_010`
- `normal_001` to `normal_010`

## Active Scripts

- `src/tissue_utils.py`: patch extraction helpers from WSI and XML annotations.
  Important fix already made: importing this module no longer deletes
  `data/patches`.
- `src/02_split_dataset.py`: creates the base train/val/test patch split by
  slide.
- `src/03_train_model.py`: trains patch-level ResNet18 models for
  `baseline`, `iter1`, `iter2`, and `iter3`.
- `src/04_eval_threshold.py`: evaluates patch thresholds on `patches_base/val`.
- `src/05_infer_wsi.py`: runs WSI inference. Default model is now
  `models/best_resnet18_patch_iter2.pt`; default output is
  `data/inference_iter2/`.
- `src/07_visualize_heatmap.py`: generates heatmap overlays from
  `data/inference_iter2/`.
- `src/09_compare_experiments.py`: compares patch-level results for
  baseline/iter1/iter2/iter3.
- `src/10_eval_wsi_connected_components.py`: WSI-level evaluation using a
  single connected-component rule.
- `src/11_eval_wsi_hybrid_rules.py`: WSI-level evaluation comparing
  `large_component`, `micro_cluster`, and `hybrid` rules.
- `src/12_extract_micro_fp_review.py`: extracts high-confidence micro-clusters
  from normal WSI for visual false-positive review and hard-negative selection.
- `src/13_prepare_iter4_dataset.py`: prepares the `iter4` training set from
  `iter2` plus selected reviewed micro false-positive hard negatives.

Legacy scripts were moved to `src/legacy/`.

## Checkpoints

The four experiment checkpoints were trained:

- `models/best_resnet18_patch_baseline.pt`
- `models/best_resnet18_patch_iter1.pt`
- `models/best_resnet18_patch_iter2.pt`
- `models/best_resnet18_patch_iter3.pt`
- `models/best_resnet18_patch_iter4.pt` is configured but not trained yet.

`models/best_resnet18_patch.pt` was also updated to the latest iter3 checkpoint
during the previous training run, but WSI evaluation is currently centered on
`best_resnet18_patch_iter2.pt`.

## Patch-Level Results

Patch-level comparison outputs:

- `outputs/experiment_comparison/dataset_summary.csv`
- `outputs/experiment_comparison/metrics.csv`
- `outputs/experiment_comparison/manuscript_table.csv`
- `outputs/experiment_comparison/manuscript_table.md`

Validation threshold was selected by maximizing tumor F1; test metrics use the
same selected threshold.

| Experiment | Threshold | Val precision | Val recall | Val F1 | Test precision | Test recall | Test F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.2 | 0.686 | 0.828 | 0.750 | 0.833 | 1.000 | 0.909 |
| iter1 | 0.3 | 0.966 | 0.966 | 0.966 | 0.909 | 1.000 | 0.952 |
| iter2 | 0.5 | 0.967 | 1.000 | 0.983 | 0.909 | 1.000 | 0.952 |
| iter3 | 0.5 | 0.966 | 0.966 | 0.966 | 1.000 | 0.700 | 0.824 |

Interpretation: `iter2` is currently the strongest patch-level compromise.

Important limitation: these are patch-level metrics, and the patch-level test
set has very few tumor patches. WSI-level evaluation is more relevant.

## WSI-Level Inference

Inference on 20 WSI was run with the iter2 model. Outputs are in:

- `data/inference_iter2/*_probs.csv`
- `data/inference_iter2/heatmaps/*_heatmap.png`

Command to rerun:

```bash
myenv311/bin/python -u src/05_infer_wsi.py --device cpu --overwrite
```

Without `--overwrite`, existing CSV files are skipped.

Generate heatmaps:

```bash
myenv311/bin/python src/07_visualize_heatmap.py
```

## WSI-Level Connected Component Results

Initial component sizes `1, 3, 5, 10` were too permissive and classified all
normal WSI as positive.

A more realistic grid was used:

- patch thresholds: `0.9, 0.8, 0.7, 0.6, 0.5`
- minimum component sizes: `10, 20, 30, 40, 50, 75, 100, 150, 200`

Outputs:

- `outputs/wsi_connected_components_iter2/per_slide_components.csv`
- `outputs/wsi_connected_components_iter2/summary_components.csv`
- `outputs/wsi_connected_components_iter2/manuscript_wsi_table.md`

Strong settings on the current 20 WSI:

- `patch_threshold=0.8`, `min_component_size=20`: sensitivity 1.000,
  specificity 1.000
- `patch_threshold=0.6`, `min_component_size=30`: sensitivity 1.000,
  specificity 1.000
- `patch_threshold=0.5`, `min_component_size=40`: sensitivity 1.000,
  specificity 1.000

Preferred interpretable setting for now:

```text
patch_threshold = 0.5
min_component_size = 40 connected patches
```

This is good for specificity, but it may miss very small metastases.

## Micro-Metastasis Concern

A large connected-component rule can miss tiny metastases. To address this,
`src/11_eval_wsi_hybrid_rules.py` compares:

- `large_component`: positive if a moderate-probability component is large
  enough.
- `micro_cluster`: positive if a tiny, very high-confidence cluster exists.
- `hybrid`: positive if either rule is positive.

Outputs:

- `outputs/wsi_hybrid_rules_iter2/per_slide_hybrid_rules.csv`
- `outputs/wsi_hybrid_rules_iter2/summary_hybrid_rules.csv`
- `outputs/wsi_hybrid_rules_iter2/manuscript_hybrid_rules.md`

Current finding:

- `micro_cluster` is sensitive but causes false positives on normal slides.
- Example: `micro_threshold=0.99`, `micro_min_component=2` produces 7 false
  positive normal WSI.
- With `micro_min_component=5`, the best micro/hybrid settings reach about
  sensitivity 1.000 and specificity 0.800.

## Micro False-Positive Review Set

`src/12_extract_micro_fp_review.py` was run with the deliberately sensitive
default setting:

```text
micro_threshold = 0.99
min_component_size = 2 connected patches
```

Outputs:

- `outputs/micro_fp_review_iter2/components.csv`: component-level summary.
- `outputs/micro_fp_review_iter2/review_template.csv`: blank review table to
  fill during visual/pathology review.
- `outputs/micro_fp_review_iter2/review_summary.md`: summarized pathology
  review and hard-negative recommendation.
- `data/review/micro_fp_iter2/`: extracted patches, contact sheets, and WSI
  overview thumbnails.

Current extraction found 11 suspicious micro-clusters on normal WSI:

- none on `normal_001`, `normal_002`, `normal_003`
- 1 each on `normal_004`, `normal_005`, `normal_006`, `normal_007`,
  `normal_008`
- 2 on `normal_009`
- 4 on `normal_010`

Pathology review conclusion:

- All 11 clusters were interpreted as benign or artefactual, confirming that
  micro-cluster detection is useful as an alert/review mode but not specific
  enough as an automatic WSI-level positive rule.
- Priority hard negatives for a future `iter4`: `normal_006` component 1 and
  `normal_009` component 2.
- Optional hard negatives: `normal_009` component 1 and `normal_010`
  components 1-4.
- Do not prioritize: `normal_004`, `normal_005`, `normal_007`, `normal_008`.

## Iter4 Preparation

`iter4` has been prepared but not trained yet.

Script:

```bash
myenv311/bin/python -u src/13_prepare_iter4_dataset.py
```

Dataset:

- Source: `data/patches_iter2/train`
- Output: `data/patches_iter4/train`
- Added only review rows marked `include_as_hard_negative=yes`
- Did not include `maybe` rows by default

Counts:

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| iter2 source | 612 | 287 | 899 |
| iter4 prepared | 618 | 287 | 905 |

Added hard negatives:

- `normal_006`, component 1: 4 patches
- `normal_009`, component 2: 2 patches

Outputs:

- `outputs/iter4_dataset/summary.md`
- `outputs/iter4_dataset/added_hard_negatives.csv`

`src/03_train_model.py` and `src/09_compare_experiments.py` now include
`iter4`.

Training command when ready:

```bash
myenv311/bin/python -u src/03_train_model.py --experiment iter4 --device cpu --epochs 10
```

Interpretation:

- Use `large_component` as the main automatic WSI decision rule.
- Use `micro_cluster` as an alert/review mode for tiny suspicious regions, not
  as a final automatic classifier yet.

## Suggested Manuscript Interpretation

Patch-level results show that iterative hard-case enrichment improves tumor
classification, with `iter2` currently the best patch-level compromise.

WSI-level results show that isolated high-probability patches are not reliable
enough: normal slides can contain small high-confidence false-positive clusters.
Connected-component post-processing greatly improves specificity.

For small metastases, a separate sensitive micro-cluster mode is clinically
motivated but should be presented as a review aid because it increases false
positives.

## Recommended Next Steps

1. Inspect heatmaps and top positive patches for the normal WSI that trigger
   micro-cluster false positives using
   `outputs/micro_fp_review_iter2/review_template.csv` and
   `data/review/micro_fp_iter2/`.
2. Extract those false-positive micro-clusters as hard negatives.
3. Train an `iter4` model with additional micro false positives.
4. Re-run:

```bash
myenv311/bin/python -u src/03_train_model.py --experiment iter3 --device cpu
myenv311/bin/python -u src/05_infer_wsi.py --device cpu --overwrite
myenv311/bin/python src/10_eval_wsi_connected_components.py
myenv311/bin/python src/11_eval_wsi_hybrid_rules.py
```

Adjust this if a new `iter4` experiment is added.

5. Add more WSI after the current 20-slide workflow is stable.
6. For thesis quality, split WSI into validation and test at the slide level,
   tune thresholds only on validation, and report final performance on held-out
   test WSI.

## Known Issues

- Git status reports a pre-existing AppleDouble pack-index issue:
  `non-monotonic index .git/objects/pack/._pack-...idx`.
- Many AppleDouble files (`._*`) exist in the project. Most scripts now ignore
  them, but they still clutter the workspace.
- Some scripts remain exploratory and are not part of the main pipeline.

## How To Resume In A New Conversation

Use this prompt:

```text
Je continue mon projet de thèse CAMELYON16. Lis PROJECT_STATE.md puis aide-moi à poursuivre à partir de la section "Recommended Next Steps".
```
