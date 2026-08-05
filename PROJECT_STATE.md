# CAMELYON16 Metastasis Detection Project State

Last updated: 2026-08-05

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
  - `data/patches_iter5/`
  - `data/patches_iter6/`
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
  `baseline`, `iter1`, `iter2`, `iter3`, `iter4`, and `iter5`.
- `src/04_eval_threshold.py`: evaluates patch thresholds on `patches_base/val`.
- `src/05_infer_wsi.py`: runs WSI inference. Default model is now
  `models/best_resnet18_patch_iter2.pt`; default output is
  `data/inference_iter2/`.
- `src/07_visualize_heatmap.py`: generates heatmap overlays from
  `data/inference_iter2/`.
- `src/09_compare_experiments.py`: compares patch-level results for
  baseline/iter1/iter2/iter3/iter4/iter5.
- `src/10_eval_wsi_connected_components.py`: WSI-level evaluation using a
  single connected-component rule.
- `src/11_eval_wsi_hybrid_rules.py`: WSI-level evaluation comparing
  `large_component`, `micro_cluster`, and `hybrid` rules.
- `src/12_extract_micro_fp_review.py`: extracts high-confidence micro-clusters
  from normal WSI for visual false-positive review and hard-negative selection.
- `src/13_prepare_iter4_dataset.py`: prepares the `iter4` training set from
  `iter2` plus selected reviewed micro false-positive hard negatives.
- `src/18_prepare_iter5_dataset.py`: prepares the `iter5` training set from
  `iter2` plus reviewed iter4 false-positive hard negatives and reviewed
  iter2 hard-positive candidates.
- `src/19_create_wsi_split.py`: creates a full WSI inventory and a slide-level
  split that tracks hard-mining usage and reserves `test_*` slides for final
  testing.
- `src/20_create_inference_queue.py`: creates resumable WSI inference queues
  from `outputs/splits/wsi_split_v1.csv`.
- `src/21_run_inference_queue.py`: runs queued WSI inference in small batches
  while updating per-slide status, runtime, output CSV path, and patch count.
- `src/22_make_portable_review_pack.py`: creates self-contained review packs
  and includes the independent junior-resident/PH review protocol.
- `src/23_prepare_iter6_dataset.py`: prepares `iter6` from the reference
  `iter2` dataset plus eight reviewed hard-negative patches per new FP
  component.

Legacy scripts were moved to `src/legacy/`.

## Checkpoints

The four experiment checkpoints were trained:

- `models/best_resnet18_patch_baseline.pt`
- `models/best_resnet18_patch_iter1.pt`
- `models/best_resnet18_patch_iter2.pt`
- `models/best_resnet18_patch_iter3.pt`
- `models/best_resnet18_patch_iter4.pt`
- `models/best_resnet18_patch_iter5.pt`
- `models/best_resnet18_patch_iter6.pt`

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

## Iter5 Preparation And Patch-Level Training

After keyboard review, a new `iter5` dataset was prepared and trained.

Hard-negative review from `outputs/iter4_fp_review/review_template.csv`:

- 12/12 components included as hard negatives.
- Added 192 normal patches.
- Categories: fibrosis/stroma benign, vessel/lumen, outside node/adipose,
  benign necrosis/coagulation, and generic artefact.

Hard-positive review from
`outputs/hard_positive_review_iter2/review_template.csv`:

- 226/238 candidates included as hard positives.
- 9 candidates excluded.
- 3 rows remained without a clear include decision.
- Included categories: metastasis border/transition, tumor in fibrosis/stroma,
  tumor in necrosis/coagulation, small tumor clusters, ITC, crushed tumor,
  tumor in artefact, and other hard tumor.

Script:

```bash
myenv_win/Scripts/python.exe src/18_prepare_iter5_dataset.py
```

Dataset:

- Source: `data/patches_iter2/train`
- Output: `data/patches_iter5/train`

Counts:

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| iter2 source | 612 | 287 | 899 |
| iter5 prepared | 804 | 513 | 1317 |

Outputs:

- `outputs/iter5_dataset/summary.md`
- `outputs/iter5_dataset/added_hard_examples.csv`

Training command:

```bash
myenv_win/Scripts/python.exe -u src/03_train_model.py --experiment iter5 --device cpu --epochs 10
```

Training result:

- Checkpoint: `models/best_resnet18_patch_iter5.pt`
- Best validation checkpoint reached at epoch 9 and matched at epoch 10.
- Final validation confusion matrix after reloading best model:

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 176 | 13 |
| True tumor | 0 | 29 |

Final validation report:

| Class | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| normal | 1.00 | 0.93 | 0.96 | 189 |
| tumor | 0.69 | 1.00 | 0.82 | 29 |

Patch-level comparison after adding `iter5`:

| Experiment | Split | Threshold | Precision | Recall | F1 | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iter2 | val | 0.5 | 0.967 | 1.000 | 0.983 | 1 | 0 |
| iter4 | val | 0.5 | 0.935 | 1.000 | 0.967 | 2 | 0 |
| iter5 | val | 0.5 | 0.879 | 1.000 | 0.935 | 4 | 0 |
| iter2 | test | 0.5 | 0.909 | 1.000 | 0.952 | 1 | 0 |
| iter4 | test | 0.5 | 0.909 | 1.000 | 0.952 | 1 | 0 |
| iter5 | test | 0.5 | 0.692 | 0.900 | 0.783 | 4 | 1 |

Interpretation:

- `iter5` is more permissive after adding many hard positives.
- It keeps high validation recall but loses patch-level specificity/precision.
- It should not replace `iter2` as the reference model without WSI-level
  evidence.
- A full WSI inference run may be useful as an experiment, but the patch-level
  signal suggests `iter5` may create more WSI false positives.

### Iter5 Targeted WSI Check

A targeted WSI inference run was performed on six normal slides that generated
larger iter4 false-positive components:

- `normal_001`
- `normal_002`
- `normal_003`
- `normal_008`
- `normal_009`
- `normal_010`

Command:

```bash
myenv_win/Scripts/python.exe -u src/05_infer_wsi.py \
  --model-path models/best_resnet18_patch_iter5.pt \
  --output-dir data/inference_iter5_targeted \
  --device cpu \
  --batch-size 256 \
  --progress-every 10 \
  --resume \
  --slides normal_001.tif normal_002.tif normal_003.tif normal_008.tif normal_009.tif normal_010.tif
```

Outputs:

- `data/inference_iter5_targeted/*_probs.csv`
- `outputs/wsi_connected_components_iter5_targeted/per_slide_components.csv`
- `outputs/wsi_connected_components_iter5_targeted/summary_components.csv`
- `outputs/wsi_iter5_targeted_summary.md`

Key targeted-normal results:

| Rule | Specificity | FP | Main issue |
| --- | ---: | ---: | --- |
| patch >= 0.5, component >= 40 | 0.833 | 1 | `normal_009` |
| patch >= 0.6, component >= 30 | 0.667 | 2 | `normal_008`, `normal_009` |
| patch >= 0.8, component >= 20 | 0.667 | 2 | `normal_008`, `normal_009` |
| patch >= 0.8, component >= 40 | 1.000 | 0 | specific on targeted normals |

Interpretation:

- `iter5` reduces several iter4 false-positive components.
- `normal_009` remains a major false-positive problem, with 4590 patches >=
  0.5 and a largest component of 153 at the `0.5/40` rule.
- `iter5` should still be considered exploratory; `iter2` remains the
  reference model unless a full WSI evaluation shows a clear benefit.

## Iter6 Dataset Preparation

The next controlled experiment uses `iter2`, not `iter5`, as its reference
dataset. This isolates the effect of the newly reviewed false positives and
does not carry forward the large hard-positive enrichment that made `iter5`
more permissive.

The reviewed iter5 FP batch contains 15 accepted components from five normal
training WSI: `normal_011`, `normal_022`, `normal_025`, `normal_028`, and
`normal_032`. All five slides were verified as `train` and are now marked as
hard-mining material in `outputs/splits/wsi_split_v1.csv`.

Preparation command:

```bash
myenv_win/Scripts/python.exe src/23_prepare_iter6_dataset.py
```

Selection:

- source dataset: `data/patches_iter2/train`;
- eight highest-probability reviewed patches per component;
- 15 components across five normal training WSI;
- 120 new hard negatives in total;
- no additional hard positives.

Dataset counts:

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| iter2 source | 612 | 287 | 899 |
| iter6 prepared | 732 | 287 | 1019 |

Added hard-negative categories:

| Category | Added patches |
| --- | ---: |
| electrocoagulation artifact | 24 |
| fibrosis/stroma benign | 16 |
| sinus histiocytosis | 48 |
| vessel/lumen | 32 |

Outputs:

- `data/patches_iter6/train/`;
- `outputs/iter6_dataset/added_hard_negatives.csv`;
- `outputs/iter6_dataset/summary.md`.

`src/03_train_model.py` and `src/09_compare_experiments.py` now recognize
`iter6`.

### Iter6 Patch-Level Training

Training command:

```bash
myenv_win/Scripts/python.exe -u src/03_train_model.py --experiment iter6 --device cpu --epochs 10
```

The best checkpoint was reached at epoch 10 and saved to
`models/best_resnet18_patch_iter6.pt`.

Final validation confusion matrix:

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 188 | 1 |
| True tumor | 0 | 29 |

Final tumor metrics:

| Model | Precision | Recall | F1 | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| iter2 | 0.967 | 1.000 | 0.983 | 1 | 0 |
| iter6 | 0.967 | 1.000 | 0.983 | 1 | 0 |

Interpretation:

- `iter6` matches `iter2` on the unchanged patch validation set.
- Adding 120 new hard negatives did not reduce validation tumor recall or
  precision.
- This does not yet prove better WSI specificity. The next check should compare
  `iter6` with `iter2` on WSI, first on the five hard-mining source slides as a
  correction check and then on new normal `train` slides for independent
  evidence.

Output:

- `outputs/iter6_training_summary.md`.

### Iter6 Targeted WSI Correction Check

`iter6` WSI inference was completed on the five normal training slides that
supplied its 15 reviewed hard-negative components:

- `normal_011`;
- `normal_022`;
- `normal_025`;
- `normal_028`;
- `normal_032`.

Inference settings were identical to the earlier WSI runs: patch size 256,
stride 128, CPU inference, and batch size 256. Outputs are in
`data/inference_iter6_hn_train_source_normals/`.

Main connected-component comparison:

| Rule | Model | FP slides | Specificity | Largest component observed |
| --- | --- | ---: | ---: | ---: |
| patch >= 0.5, component >= 40 | iter2 | 5/5 | 0.000 | 212 |
| patch >= 0.5, component >= 40 | iter5 | 5/5 | 0.000 | 2632 |
| patch >= 0.5, component >= 40 | iter6 | 2/5 | 0.600 | 111 |
| patch >= 0.6, component >= 30 | iter2 | 4/5 | 0.200 | 149 |
| patch >= 0.6, component >= 30 | iter5 | 5/5 | 0.000 | 2272 |
| patch >= 0.6, component >= 30 | iter6 | 3/5 | 0.400 | 105 |
| patch >= 0.8, component >= 20 | iter2 | 4/5 | 0.200 | 91 |
| patch >= 0.8, component >= 20 | iter5 | 5/5 | 0.000 | 615 |
| patch >= 0.8, component >= 20 | iter6 | 3/5 | 0.400 | 64 |

At the main `0.5 / 40` rule, `iter6` corrects `normal_011`, `normal_025`, and
`normal_032`. `normal_022` and `normal_028` remain false-positive. This is an
expected training-source correction check, not independent performance
evidence. The next experiment must use new normal `train` WSI that have never
been reviewed or included in training.

Outputs:

- `outputs/wsi_connected_components_iter6_hn_train_source_normals/`;
- `outputs/wsi_iter2_iter5_iter6_hn_source_comparison.csv`;
- `outputs/wsi_iter2_iter5_iter6_hn_source_summary.md`.

## Iter6 Generalization Pilot On Unseen Normal Train WSI

On 2026-07-18, `iter2` and `iter6` were compared on five normal `train` WSI
that had never been reviewed, explored, or used for hard mining:
`normal_033` to `normal_037`. The two models used identical WSI inference
settings (patch size 256, stride 128, CPU, batch size 256).

| WSI rule | Model | FP slides | Specificity | Positive patches | Largest component |
| --- | --- | ---: | ---: | ---: | ---: |
| patch >= 0.5, component >= 40 | iter2 | 4/5 | 0.200 | 26,749 | 1,043 |
| patch >= 0.5, component >= 40 | iter6 | 3/5 | 0.400 | 8,655 | 100 |
| patch >= 0.6, component >= 30 | iter2 | 5/5 | 0.000 | 21,820 | 633 |
| patch >= 0.6, component >= 30 | iter6 | 3/5 | 0.400 | 6,907 | 85 |
| patch >= 0.8, component >= 20 | iter2 | 4/5 | 0.200 | 12,648 | 292 |
| patch >= 0.8, component >= 20 | iter6 | 3/5 | 0.400 | 3,817 | 55 |

At the main `0.5 / 40` rule, iter6 reduces the total positive-patch burden by
67.6% and the largest connected component by 90.4% relative to iter2. It
corrects `normal_036`; `normal_034`, `normal_035`, and `normal_037` remain
false-positive. `normal_035` deserves special review because its FP burden is
higher with iter6 than with iter2.

This is independent evidence relative to the hard-mining source slides, but it
is still an internal pilot on the `train` split, not final validation evidence.
The remaining iter6 FP components must be reviewed independently before any
new injection.

These historical numbers were later found to use the raw Otsu mask rather than
the cleaned mask returned by the tissue-mask pipeline. They are retained here
for traceability but must not be used as the current WSI comparison.

Outputs:

- `outputs/wsi_connected_components_iter2_unseen_train_normals_033_037/`;
- `outputs/wsi_connected_components_iter6_unseen_train_normals_033_037/`;
- `outputs/wsi_iter2_iter6_unseen_train_normals_033_037_comparison.csv`;
- `outputs/wsi_iter2_iter6_unseen_train_normals_033_037_summary.md`.

### Tissue-Mask Root Cause And Corrected WSI Pilot

The review of `normal_035` with WSI context showed that all 10 extracted
components were outside the lymph node. Code inspection then identified the
cause: `make_tissue_mask()` returns `(raw, cleaned, threshold)`, but active
callers unpacked its first return value and therefore used the raw Otsu mask.

The mask contract is now explicit:

- `make_clean_tissue_mask()` returns the cleaned mask used for inference and
  extraction;
- active WSI inference and hard-negative extraction call this helper;
- `tests/test_tissue_mask_contract.py` protects the raw-versus-cleaned return
  contract.

Exact inference was resumed on the cleaned mask for `normal_033` to
`normal_037`. Cleaning is not a simple subset operation: morphological closing,
hole filling, and dilation can also add valid internal centers. Therefore the
corrected results are a full clean-mask recalculation, not merely a post-hoc
removal of old detections.

At the frozen main rule (`patch probability >= 0.5`, component size >= 40):

| Slide | iter2 positive patches | iter2 max component | iter2 FP | iter6 positive patches | iter6 max component | iter6 FP |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| normal_033 | 1,136 | 35 | no | 1,165 | 55 | yes |
| normal_034 | 14,386 | 762 | yes | 6,353 | 425 | yes |
| normal_035 | 286 | 16 | no | 429 | 35 | no |
| normal_036 | 5,735 | 1,047 | yes | 1,355 | 45 | yes |
| normal_037 | 9,614 | 885 | yes | 5,054 | 161 | yes |

Corrected aggregate comparison:

| Model | FP slides | Specificity | Positive patches | Largest component |
| --- | ---: | ---: | ---: | ---: |
| iter2 | 3/5 | 0.400 | 31,157 | 1,047 |
| iter6 | 4/5 | 0.200 | 14,356 | 425 |

Thus `normal_035` is negative for both models after correction, confirming that
its 10 reviewed components were ROI/mask errors and must not be injected as
classifier hard negatives. Iter6 still reduces total positive-patch burden by
53.9% and the largest component by 59.4% relative to iter2, but it does not
improve slide-level specificity on this five-slide pilot. No new training
iteration should be created before visual audit of the corrected mask overlays.

Corrected outputs:

- `data/inference_iter2_unseen_train_normals_033_037_clean_mask/`;
- `data/inference_iter6_unseen_train_normals_033_037_clean_mask/`;
- `outputs/wsi_connected_components_iter2_unseen_train_normals_033_037_clean_mask/`;
- `outputs/wsi_connected_components_iter6_unseen_train_normals_033_037_clean_mask/`;
- `outputs/wsi_iter2_iter6_unseen_train_normals_033_037_mask_comparison.csv`;
- `outputs/wsi_iter2_iter6_unseen_train_normals_033_037_clean_mask_summary.md`.

### Clean-Mask Visual Audit And Replacement Review Pack

Raw-versus-cleaned mask audit figures were exported for all five slides. Each
figure shows the WSI thumbnail, raw Otsu overlay, cleaned overlay, and pixels
added/removed by morphology. `normal_035` falls from 1.6% raw-mask coverage to
1.0% cleaned coverage; the cleaned mask keeps the dense nodal tissue and
removes the extra-nodal regions responsible for the former review pack.

Output:

- `outputs/tissue_mask_audit_normals_033_037_clean/`.

The corrected iter6 connected components were then extracted at the frozen
`0.5 / 40` rule. This replacement pack contains 37 components:

| Slide | Corrected components | Largest component |
| --- | ---: | ---: |
| normal_033 | 1 | 55 |
| normal_034 | 19 | 425 |
| normal_035 | 0 | 35 (below decision threshold) |
| normal_036 | 1 | 45 |
| normal_037 | 16 | 161 |

Visual QA of the WSI overviews confirms readable component boxes; preliminary
inspection of `normal_034` and `normal_037` places the boxes on nodal tissue.
The 37 components still require pathological review before any hard-negative
selection.

Replacement review outputs:

- `data/review/iter6_clean_mask_unseen_train_fp_components/`;
- `outputs/iter6_clean_mask_unseen_train_fp_review/`;
- `portable_review_packs/iter6_clean_mask_unseen_train_fp_review/`.

The portable pack supports two distinct phases without overwriting the initial
review. `run_review_junior_windows.cmd` records the resident's independent
answers in `review_junior.csv`. Later,
`run_review_consensus_with_junior_windows.cmd` displays those frozen answers
in the review window and writes only the joint resident/PH decision to
`review_consensus.csv`. Updating an existing pack now preserves all reviewer
CSV files.

### Iter6 Unseen-WSI FP Review Pack

On 2026-07-19, every iter6 connected component meeting the frozen main rule
(`patch probability >= 0.5`, component size >= 40, stride 128) was extracted
from the three remaining FP slides. No candidate has been injected into a
training dataset.

| Slide | Components to review | Largest component |
| --- | ---: | ---: |
| normal_034 | 4 | 82 patches |
| normal_035 | 10 | 99 patches |
| normal_037 | 2 | 100 patches |
| **Total** | **16** | **100 patches** |

Each component has up to 16 individual 256 x 256 patches, an annotated contact
sheet, and a slide overview. Visual QA confirmed that the contact sheets and
overview boxes are readable. The portable packs contain 16 review rows and 19
referenced images with no missing paths.

Local outputs:

- `data/review/iter6_unseen_train_fp_components/` (individual patches and
  source review images);
- `outputs/iter6_unseen_train_fp_review/` (component table, blank template,
  and summary);
- `portable_review_packs/iter6_unseen_train_fp_review/` (master pack);
- `portable_review_packs/iter6_unseen_train_fp_review_junior/` (independent
  junior-resident copy);
- `portable_review_packs/iter6_unseen_train_fp_review_ph/` (independent PH
  copy).

The pack generator now creates separate blank `review_junior.csv`,
`review_ph.csv`, and `review_consensus.csv` files plus reviewer-specific
Windows and macOS launchers. The consensus file must remain blank until both
initial reviews have been frozen.

### Iter6 Inter-Reviewer Comparison

The independent junior-resident and PH reviews were completed on 16/16
components and compared on 2026-07-25. The two original CSV files remain
separate and unchanged; the consensus file is still blank.

| Field | Exact agreement | Agreement rate | Cohen's kappa |
| --- | ---: | ---: | ---: |
| Binary label (normal/tumor) | 16/16 | 100.0% | not calculable |
| Morphology category | 3/16 | 18.8% | 0.171 |
| Difficulty type | 15/16 | 93.8% | 0.000 |
| Include as hard negative | 15/16 | 93.8% | 0.000 |

Interpretation:

- both observers classify all 16 detections as normal/benign, so there is no
  disagreement about the binary nature of these false positives;
- fine morphology classification is poorly reproducible in this small batch;
- all 10 `normal_035` components differ: the junior resident mainly used
  fibrosis/stroma or artifact categories, whereas the PH classified all 10 as
  `outside_node_adipose`;
- `normal_037` component 1 is the only disagreement affecting difficulty and
  hard-negative inclusion: junior `necrosis_coagulation_benign` / include,
  versus PH `benign_not_useful` / do not include;
- 10 of 13 morphology disagreements come from one WSI (`normal_035`), so
  component-level observations are clustered and kappa must remain
  descriptive;
- WSI-context review resolved those 10 `normal_035` rows as `outside_roi`;
  their initial morphology disagreement reflects missing spatial context and
  the raw-mask bug, not a pure histological disagreement;
- kappa is not calculable for the binary field because both reviewers use only
  one category. Kappa is zero for difficulty and inclusion because the junior
  review has no category variation; this does not negate the high raw
  agreement and illustrates the prevalence problem.

Comparison workbook:

- `outputs/interreview_iter6_20260725/comparaison_interreview_iter6.xlsx`

The workbook contains the untouched raw responses, the paired comparison,
the 13 morphology disagreements, transparent marginal-count/kappa
calculations, a corrected-mask WSI sheet, and a synthesis sheet. Formula and
visual QA found no errors.

## Suggested Manuscript Interpretation

Patch-level results show that iterative hard-case enrichment improves tumor
classification, with `iter2` currently the best patch-level compromise.

WSI-level results show that isolated high-probability patches are not reliable
enough: normal slides can contain small high-confidence false-positive clusters.
Connected-component post-processing greatly improves specificity.

For small metastases, a separate sensitive micro-cluster mode is clinically
motivated but should be presented as a review aid because it increases false
positives.

## Full WSI Inventory And Slide-Level Split v1

After downloading the broader CAMELYON16 WSI set, a slide-level inventory and
split were generated to make future comparisons methodologically cleaner.

Script:

```bash
myenv_win/Scripts/python.exe src/19_create_wsi_split.py
```

Outputs:

- `outputs/splits/wsi_inventory_v1.csv`
- `outputs/splits/wsi_split_v1.csv`
- `outputs/splits/wsi_split_v1_summary.md`

Current root-level WSI inventory:

| Group | Count |
| --- | ---: |
| normal | 155 |
| tumor | 105 |
| test | 125 |

Notes:

- `data/wsi/background_tissue/` contains tissue-mask images and is not counted
  as raw WSI.
- `data/wsi/images/` contains extra/partial-looking WSI files and is not
  counted in the root-level split.
- Missing expected root-level WSI: `normal_086`; `tumor_089`, `tumor_090`,
  `tumor_092` to `tumor_095`; `test_001`, `test_002`, `test_049`,
  `test_104`, `test_107`.
- XML files without matching root-level WSI currently include `test_001`,
  `test_002`, `test_104`, `tumor_089`, `tumor_090`, and `tumor_092` to
  `tumor_095`.

Labeling convention in `wsi_split_v1.csv`:

- `normal_*`: label `normal`
- `tumor_*`: label `tumor`
- `test_*` with XML: label `tumor`
- `test_*` without XML: label `normal` by assumption

This `test_*` convention should be verified against official CAMELYON16 test
metadata before final manuscript reporting.

Split v1:

| Split | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| train | 126 | 86 | 212 |
| val | 29 | 19 | 48 |
| test_final | 79 | 46 | 125 |

Hard-mining tracking:

- 20 slides are marked as used for hard mining and forced into `train`.
- `normal_001` to `normal_010` were used in false-positive review and/or prior
  WSI exploration.
- `tumor_001` to `tumor_010` were used in hard-positive review and prior WSI
  exploration.
- No slide marked as hard-mining material is assigned to `test_final`.

Recommended future evaluation workflow:

1. Use `train` for patch extraction, model training, and hard-example
   enrichment.
2. Use `val` for threshold selection and WSI connected-component rule tuning.
3. Use `test_final` only once the model and WSI decision rules are frozen.

## Hard-Mining Protocol And Inference Queue

A first hard-mining protocol and queue-based inference workflow were added.

Protocol:

- `outputs/hard_mining_protocol_v1.md`

The FP review procedure was updated on 2026-07-18 for the next hard-mining
batch. The junior resident and the senior pathologist (`PH`) will first review
the same candidates independently in separate files. Their initial answers
will then be compared before a consensus discussion. The comparison will
report exact agreement percentages for the main review fields and Cohen's
kappa when appropriate; the consensus must be stored separately and must not
overwrite either initial assessment.

Queue scripts:

- `src/20_create_inference_queue.py`
- `src/21_run_inference_queue.py`

The first queue targets 20 normal training slides not already used for hard
mining or prior WSI exploration:

```bash
myenv_win/Scripts/python.exe src/20_create_inference_queue.py \
  --experiment iter2 \
  --purpose hard_negative_train_screen \
  --splits train \
  --labels normal \
  --limit 20 \
  --output-csv iter2_hn_train_normals_queue.csv
```

Output:

- `outputs/inference_queues/iter2_hn_train_normals_queue.csv`

Dry-run validation of the queue runner was completed with `--max-slides 0`:

```bash
myenv_win/Scripts/python.exe src/21_run_inference_queue.py \
  --queue-csv outputs/inference_queues/iter2_hn_train_normals_queue.csv \
  --model-path models/best_resnet18_patch_iter2.pt \
  --output-dir data/inference_iter2_hn_train_screen \
  --device cpu \
  --max-slides 0
```

To start real inference, run the same command with a small batch size such as
`--max-slides 2` or `--max-slides 5`.

### Iter7 Dataset Construction

On 2026-08-01, the corrected clean-mask consensus was frozen for all 37
reviewed iter6 false-positive components. Every selected row is labelled
`normal`, `hard_negative`, and `include_as_hard_negative=yes`. The final
morphology distribution is 20 `vessel_lumen`, 13
`fibrosis_stroma_benign`, and 4 `sinus_histiocytosis` components.

`iter7` was built cumulatively from `iter6`, preserving its 120 previously
reviewed hard negatives and adding 136 patches from the corrected consensus.
Selection is capped at four patches per component and 64 new patches per WSI.
A deterministic rank round-robin allocation keeps all 37 components
represented despite the WSI cap: 25 components contribute four patches and
12 contribute three patches.

| Source WSI | Added patches |
| --- | ---: |
| normal_033 | 4 |
| normal_034 | 64 |
| normal_036 | 4 |
| normal_037 | 64 |

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| iter6 | 732 | 287 | 1,019 |
| iter7 | 868 | 287 | 1,155 |

The independent `review_ph.csv` remains blank. Therefore the 67.6% exact
category match (25/37) between the junior review and final consensus must be
reported as junior-versus-adjudicated-consensus agreement, not as an
independent junior-versus-PH inter-reviewer measurement.

Outputs:

- `src/24_prepare_iter7_dataset.py`;
- `data/patches_iter7/train/`;
- `outputs/iter7_dataset/added_hard_negatives.csv`;
- `outputs/iter7_dataset/summary.md`.

### Iter7 Training

On 2026-08-01, `iter7` was trained for 10 epochs on CPU using the same frozen
recipe and unchanged patch validation set as `iter6`. The best checkpoint was
selected at epoch 9 by tumor F1 at threshold 0.2.

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 189 | 0 |
| True tumor | 0 | 29 |

Both tumor precision and recall are 1.000 on the 218-patch validation set.
Compared with `iter6`, this removes the single validation normal false positive
while preserving all tumor detections. This does not establish WSI-level
superiority; clean-mask WSI validation is still required.

Outputs:

- `models/best_resnet18_patch_iter7.pt`;
- `outputs/iter7_training_summary.md`.

### Iter7 WSI Validation

On 2026-08-05, iter7 WSI inference was completed on all 48 `val` slides
(29 normal, 19 tumor) using the corrected tissue mask. `test_final` remained
untouched. With the frozen WSI decision rule (patch threshold 0.5, minimum
connected component size 40), the result was:

| Sensitivity | Specificity | Precision | F1 | Accuracy | TP | FP | FN | TN |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.842 | 0.448 | 0.500 | 0.627 | 0.604 | 16 | 16 | 3 | 13 |

A validation-only grid over patch thresholds 0.5-0.9 and component sizes
20-1000 did not find a rule with sensitivity at least 0.80 and specificity
above 0.448. The failure therefore cannot be corrected by a simple WSI-rule
change without a major sensitivity loss.

The 16 false-positive validation slides were extracted for diagnostic use
only. Their largest components contain strongly positive benign patterns,
especially histiocyte-rich/reactive tissue, dense eosinophilic fibrous stroma,
and connective/vascular or processing artefacts. Validation patches must not
be injected into training.

Outputs:

- `data/inference_iter7_val/`;
- `outputs/wsi_connected_components_iter7_val/`;
- `outputs/wsi_connected_components_iter7_val_grid/`;
- `outputs/iter7_val_fp_diagnostic/`;
- `data/review/iter7_val_fp_diagnostic/`.

### Iter8 Hard-Negative Screen

Iter8 hard-negative discovery started on 2026-08-05 using iter7 on ten
previously unused normal `train` WSI: `normal_013` to `normal_021`, plus
`normal_023`. Inference is resumable, CPU-only, stride 128, batch size 128,
eight OpenMP/MKL threads, normal process priority, and strictly one WSI at a
time. Neither `val` nor `test_final` is used for candidate generation.

Outputs in progress:

- `outputs/inference_queues/iter8_hn_train_normals_queue.csv`;
- `data/inference_iter7_iter8_hn_train_screen/`.

When all ten WSI are complete, connected false-positive components will be
extracted at threshold 0.5 and minimum size 40 into
`outputs/iter8_hn_train_fp_review/` and packaged in
`portable_review_packs/iter8_hn_train_fp_review/`. Human review is required
before building or training iter8.

## Recommended Next Steps

1. Complete the ten-slide iter8 hard-negative screen on normal `train` WSI.
2. Review the extracted components independently and freeze a separate
   consensus before adding any patch to iter8.
3. Build iter8 cumulatively from iter7, retrain, and evaluate on `val` only.
4. Keep `test_final` untouched until both the model and WSI decision rule are
   frozen.

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
