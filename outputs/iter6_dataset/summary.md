# Iter6 Dataset Preparation

`iter6` is built from `data/patches_iter2/train` plus the newly reviewed iter5 false-positive hard negatives.

## Selection

- Reference dataset: `iter2`
- Included review decision: `include_as_hard_negative=yes`
- Source slides: 5 (all checked as `train`)
- Reviewed components: 15
- Patches per component: 8
- Added hard-negative patches: 120

## Counts

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| Source iter2 | 612 | 287 | 899 |
| Iter6 | 732 | 287 | 1019 |

## Added Hard-Negative Categories

| Category | Added patches |
| --- | ---: |
| electrocoagulation_artifact | 24 |
| fibrosis_stroma_benign | 16 |
| sinus_histiocytosis | 48 |
| vessel_lumen | 32 |
