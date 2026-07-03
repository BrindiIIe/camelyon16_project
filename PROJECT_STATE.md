# CAMELYON16 Metastasis Detection Project State

Last updated: 2026-07-03

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
- Iter4 WSI inference outputs: `data/inference_iter4/`

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
- `models/best_resnet18_patch_iter4.pt`

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

`iter4` has been prepared and trained.

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

This command was run successfully on 2026-07-02.

Training result:

- Checkpoint: `models/best_resnet18_patch_iter4.pt`
- Best validation checkpoint reached at epoch 7 and matched at epoch 8.
- Final validation confusion matrix after reloading best model:

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 185 | 4 |
| True tumor | 0 | 29 |

Final validation report:

| Class | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| normal | 1.00 | 0.98 | 0.99 | 189 |
| tumor | 0.88 | 1.00 | 0.94 | 29 |

Output summary:

- `outputs/iter4_training_summary.md`

## Iter4 WSI Inference And Evaluation

`src/05_infer_wsi.py` was updated to make WSI inference easier to monitor and
interrupt:

- writes a `*_probs.partial.csv` during each slide instead of keeping all
  results only in memory
- renames the partial file to `*_probs.csv` only when the slide is complete
- supports `--resume` to continue from an interrupted partial CSV
- supports `--progress-every N` to print batch progress, throughput, and ETA

Recommended iter4 targeted WSI command after this update:

```bash
myenv311/bin/python -u src/05_infer_wsi.py \
  --model-path models/best_resnet18_patch_iter4.pt \
  --output-dir data/inference_iter4_micro_normals \
  --device cpu \
  --batch-size 256 \
  --progress-every 5 \
  --resume \
  --slides normal_004.tif normal_005.tif normal_006.tif normal_007.tif normal_008.tif normal_009.tif normal_010.tif
```

Full 20-slide iter4 WSI inference was completed on 2026-07-03 with:

```bash
myenv311/bin/python -u src/05_infer_wsi.py \
  --model-path models/best_resnet18_patch_iter4.pt \
  --output-dir data/inference_iter4 \
  --device cpu \
  --batch-size 256 \
  --progress-every 5 \
  --resume \
  --slides tumor_001.tif tumor_002.tif tumor_003.tif tumor_004.tif tumor_005.tif tumor_006.tif tumor_007.tif tumor_008.tif tumor_009.tif tumor_010.tif normal_001.tif normal_002.tif normal_003.tif normal_004.tif normal_005.tif normal_006.tif normal_007.tif normal_008.tif normal_009.tif normal_010.tif
```

Observed CPU throughput was about 22-25 patches/second on CPU.

Outputs:

- `data/inference_iter4/*_probs.csv`
- `outputs/wsi_connected_components_iter4/per_slide_components.csv`
- `outputs/wsi_connected_components_iter4/summary_components.csv`
- `outputs/wsi_connected_components_iter4/manuscript_wsi_table.md`
- `outputs/wsi_hybrid_rules_iter4/per_slide_hybrid_rules.csv`
- `outputs/wsi_hybrid_rules_iter4/summary_hybrid_rules.csv`
- `outputs/wsi_hybrid_rules_iter4/manuscript_hybrid_rules.md`
- `outputs/wsi_iter2_vs_iter4_summary.md`

Evaluation commands:

```bash
myenv311/bin/python src/10_eval_wsi_connected_components.py \
  --csv-dir data/inference_iter4 \
  --output-dir outputs/wsi_connected_components_iter4

myenv311/bin/python src/11_eval_wsi_hybrid_rules.py \
  --csv-dir data/inference_iter4 \
  --output-dir outputs/wsi_hybrid_rules_iter4
```

Main WSI-level finding:

- Iter4 is not better than iter2 on the current 20 WSI.
- Iter4 keeps high sensitivity, but WSI-level specificity is worse.
- Best iter4 connected-component setting observed:
  `patch_threshold=0.7`, `min_component_size=75`: sensitivity 1.000,
  specificity 0.800, precision 0.833, F1 0.909.
- By comparison, iter2 has multiple connected-component settings with
  sensitivity 1.000 and specificity 1.000 on the same 20 WSI.
- Therefore, `iter2` remains the reference model for the thesis pipeline.

Comparable connected-component examples:

| Rule | Model | Sensitivity | Specificity | Precision | F1 | FP |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| patch >= 0.60, component >= 30 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| patch >= 0.60, component >= 30 | iter4 | 1.000 | 0.400 | 0.625 | 0.769 | 6 |
| patch >= 0.50, component >= 40 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| patch >= 0.50, component >= 40 | iter4 | 1.000 | 0.400 | 0.625 | 0.769 | 6 |
| patch >= 0.80, component >= 20 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| patch >= 0.80, component >= 20 | iter4 | 1.000 | 0.200 | 0.556 | 0.714 | 8 |

## Iter4 Micro False-Positive Patch Check

A faster targeted check was added:

```bash
myenv311/bin/python -u src/14_compare_micro_fp_patch_probs.py --device cpu
```

This compares `iter2` and `iter4` probabilities on the 37 already extracted
micro false-positive review patches from `data/review/micro_fp_iter2/`.

Outputs:

- `outputs/micro_fp_iter2_vs_iter4/patch_probs.csv`
- `outputs/micro_fp_iter2_vs_iter4/summary.md`

Key finding:

- On the two reviewed `yes` components used as hard negatives for `iter4`,
  probabilities dropped dramatically:
  - `normal_006` component 1: mean iter2 `1.000`, mean iter4 `0.034`
  - `normal_009` component 2: mean iter2 `0.995`, mean iter4 `0.013`
- Some non-included false positives remain high:
  - `normal_007` component 1: mean iter2 `0.998`, mean iter4 `0.999`
  - `normal_008` component 1: mean iter2 `0.998`, mean iter4 `0.923`

Interpretation:

- `iter4` learned the specific hard negatives it was trained on.
- It does not yet prove better WSI-level specificity because some other benign
  mimics remain high-confidence.
- Before another full WSI run, improve `05_infer_wsi.py` with progress logging
  and/or faster batching.

## Iter4 False-Positive Component Review

Because full WSI evaluation showed that iter4 is less specific than iter2, a
new script extracts larger iter4 false-positive connected components from
normal WSI:

```bash
myenv311/bin/python src/15_extract_iter4_fp_components.py
```

Default extraction settings:

- input: `data/inference_iter4`
- slides: `normal_001` to `normal_010`
- threshold: `0.60`
- minimum component size: `30` connected patches
- maximum components per slide: `5`
- maximum extracted patches per component: `16`

Outputs:

- `outputs/iter4_fp_review/components.csv`
- `outputs/iter4_fp_review/review_template.csv`
- `outputs/iter4_fp_review/summary.md`
- `data/review/iter4_fp_components/`

Current extraction found 12 iter4 false-positive components:

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| `normal_001` | 1 | 89 | 1.000 |
| `normal_002` | 2 | 75 | 1.000 |
| `normal_003` | 5 | 201 | 1.000 |
| `normal_008` | 2 | 45 | 1.000 |
| `normal_009` | 1 | 32 | 0.998 |
| `normal_010` | 1 | 90 | 0.999 |

Next action: review these contact sheets as benign/artefact/tissue-type
mimics and mark which components should become hard negatives for iter5.

## Hard Positive Candidate Review

To balance hard-negative mining with difficult tumor examples, a new script
extracts hard-positive candidates from annotated tumor WSI using the reference
iter2 inference outputs:

```bash
myenv311/bin/python src/16_extract_hard_positive_candidates.py
```

Default extraction settings:

- input inference: `data/inference_iter2`
- slides: `tumor_001` to `tumor_010`
- low probability threshold: `0.50`
- intermediate probability threshold: `0.80`
- edge margin: `256` pixels
- maximum selected candidates per slide: `24`

The script selects annotated tumor patches that are low/intermediate confidence
for iter2 and prioritizes patches near annotation borders. These are candidate
hard positives, not automatically accepted training samples.

Outputs:

- `outputs/hard_positive_review_iter2/candidates.csv`
- `outputs/hard_positive_review_iter2/review_template.csv`
- `outputs/hard_positive_review_iter2/summary.md`
- `data/review/hard_positive_iter2/`

Current extraction selected 238 hard-positive candidates:

| Slide | Annotated tumor candidates | Eligible hard positives | Selected | Lowest prob |
| --- | ---: | ---: | ---: | ---: |
| `tumor_001` | 688 | 313 | 24 | 0.042 |
| `tumor_002` | 35 | 33 | 24 | 0.026 |
| `tumor_003` | 421 | 236 | 24 | 0.010 |
| `tumor_004` | 323 | 209 | 24 | 0.000 |
| `tumor_005` | 143 | 107 | 24 | 0.017 |
| `tumor_006` | 105 | 92 | 24 | 0.077 |
| `tumor_007` | 147 | 118 | 24 | 0.321 |
| `tumor_008` | 22 | 22 | 22 | 0.002 |
| `tumor_009` | 50855 | 23858 | 24 | 0.000 |
| `tumor_010` | 24 | 24 | 24 | 0.953 |

Next action: review these candidates as true tumor vs annotation-border noise,
artefact, necrosis/fibrosis, crushed tumor, or uninformative patch. Accepted
rows can become hard positives for iter5.

## Keyboard Review Tool

`src/17_review_candidates_keyboard.py` provides a fast keyboard-based review
workflow. It displays each candidate image/contact sheet, updates the review
CSV in place, and copies the displayed image into a category folder under
`data/review_sorted/`.

The review CSV keeps three separate concepts:

- `binary_label`: `tumor` / `normal`
- `morphology_category`: pathologist-facing category
- `difficulty_type`: `hard_positive`, `hard_negative`, `border_transition`,
  `easy_or_not_useful`, `uncertain`, or `reject`

Review iter4 false positives / hard negatives:

```bash
myenv311/bin/python src/17_review_candidates_keyboard.py --mode fp
```

Useful `fp` keys:

- `h`: other hard negative, include yes
- `m`: macrophage/histiocyte, include yes
- `s`: sinus histiocytosis, include yes
- `f`: benign fibrosis/stroma, include yes
- `g`: electrocoagulation artifact, include yes
- `c`: benign crush artifact, include yes
- `v`: vessel/lumen, include yes
- `o`: outside node/adipose, include yes
- `n`: benign necrosis/coagulation, include yes
- `a`: generic artifact, include yes
- `b`: benign but not useful, include no
- `u`: uncertain, review later
- `x`: reject/uninformative, include no

Review iter2 hard-positive candidates:

```bash
myenv311/bin/python src/17_review_candidates_keyboard.py --mode hp
```

Useful `hp` keys:

- `t`: other hard tumor, include yes
- `m`: micrometastasis, include yes
- `i`: isolated tumor cells / ITC, include yes
- `s`: small tumor cluster, include yes
- `c`: crushed tumor, include yes
- `f`: tumor in fibrosis/stroma, include yes
- `n`: tumor in necrosis/coagulation, include yes
- `a`: tumor in artifact, include yes
- `b`: metastasis border / transition, include yes
- `e`: easy tumor, include no
- `p`: partial/border uncertain
- `r`: artifact or annotation noise, include no
- `x`: reject/uninformative, include no

Shared controls:

- `space` or right arrow: skip current row
- left arrow or backspace: go back one row
- `q`: quit and keep CSV updates already written

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
