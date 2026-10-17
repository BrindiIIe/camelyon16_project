# Corrected-mask WSI comparison: iter2 versus iter6

Date: 2026-07-25

## Cause and correction

`make_tissue_mask()` returns `(raw_mask, cleaned_mask, threshold)`, but the WSI
inference and related extraction paths selected the first value. Historical
WSI results therefore used the raw Otsu mask instead of the intended cleaned
mask.

The pipeline now calls the explicit `make_clean_tissue_mask()` accessor. A
regression test verifies that this accessor returns the cleaned mask and not
the raw diagnostic mask.

Existing probabilities inside the corrected mask were reused. Only cleaned
mask centers without an existing probability were inferred, using the same
models, patch size 256, stride 128, and batch size 256.

## Main-rule comparison

| Mask | Model | FP slides | Specificity | Positive patches | Largest component |
| --- | --- | ---: | ---: | ---: | ---: |
| Raw historical | iter2 | 4/5 | 0.200 | 26,749 | 1,043 |
| Cleaned corrected | iter2 | 3/5 | 0.400 | 31,157 | 1,047 |
| Raw historical | iter6 | 3/5 | 0.400 | 8,655 | 100 |
| Cleaned corrected | iter6 | 4/5 | 0.200 | 14,356 | 425 |

Under the corrected mask, `normal_035` becomes negative for both models:

- iter2: largest component 16;
- iter6: largest component 35.

Both are below the frozen minimum component size of 40. The ten reviewed
`normal_035` components were therefore mask/ROI failures and should not be
injected as classifier hard negatives.

## Corrected main-rule result by slide

| Slide | iter2 positive patches | iter2 largest component | iter2 FP | iter6 positive patches | iter6 largest component | iter6 FP |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| normal_033 | 1,136 | 35 | no | 1,165 | 55 | yes |
| normal_034 | 14,386 | 762 | yes | 6,353 | 425 | yes |
| normal_035 | 286 | 16 | no | 429 | 35 | no |
| normal_036 | 5,735 | 1,047 | yes | 1,355 | 45 | yes |
| normal_037 | 9,614 | 885 | yes | 5,054 | 161 | yes |

Iter6 still reduces positive-patch burden by 53.9% and the maximum component
size by 59.4% relative to iter2, but it does not improve slide-level
specificity on this five-slide pilot (`4/5` versus `3/5` false-positive
slides).

## Important mask behavior

The corrected mask is not simply a stricter subset of the raw mask. Closing,
hole filling, and dilation consolidate large tissue masses and add valid
centers in some pale/internal regions:

- historical raw-mask centers across the five slides: 384,704;
- corrected cleaned-mask centers: 458,833;
- `normal_035` decreases from 15,436 to 12,412 centers;
- the other four slides gain centers inside consolidated tissue masses.

This explains why `normal_035` is corrected while new connected components
appear on `normal_033` and `normal_036`.

## Decision

Do not create a new training iteration yet. First:

1. record the ten `normal_035` components as `outside_node_adipose /
   outside_roi` and exclude them from classifier hard-negative injection;
2. visually audit cleaned-mask overlays on all five slides, especially the
   filled/dilated regions that created new centers;
3. decide whether the current generic tissue mask is sufficient or whether a
   lymph-node ROI strategy is required;
4. review only the remaining corrected iter6 FP components before considering
   additional hard-negative training.

Outputs:

- `outputs/wsi_connected_components_iter2_unseen_train_normals_033_037_clean_mask/`;
- `outputs/wsi_connected_components_iter6_unseen_train_normals_033_037_clean_mask/`;
- `outputs/wsi_iter2_iter6_unseen_train_normals_033_037_mask_comparison.csv`.
