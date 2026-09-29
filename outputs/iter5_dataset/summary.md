# Iter5 Dataset Preparation

`iter5` is built from `data/patches_iter2/train` plus reviewed iter4 false-positive hard negatives and iter2 hard-positive candidates.

## Selection

- Included hard negatives: `include_as_hard_negative=yes`
- Included hard positives: `include_as_hard_positive=yes`
- Added hard-negative patches: 192
- Added hard-positive patches: 226

## Counts

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| Source iter2 | 612 | 287 | 899 |
| Iter5 | 804 | 513 | 1317 |

## Added Hard-Negative Categories

| Category | Added patches |
| --- | ---: |
| fibrosis_stroma_benign | 112 |
| generic_artifact | 16 |
| necrosis_coagulation_benign | 16 |
| outside_node_adipose | 16 |
| vessel_lumen | 32 |

## Added Hard-Positive Categories

| Category | Added patches |
| --- | ---: |
| crushed_tumor | 4 |
| isolated_tumor_cells | 16 |
| metastasis_border_transition | 71 |
| other_hard_tumor | 2 |
| small_tumor_cluster | 34 |
| tumor_in_artifact | 4 |
| tumor_in_fibrosis_stroma | 65 |
| tumor_in_necrosis_coagulation | 30 |
