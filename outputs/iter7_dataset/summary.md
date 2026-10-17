# Iter7 Dataset Preparation

`iter7` is cumulative: `iter6` plus hard negatives from the corrected iter6 clean-mask consensus.

## Selection contract

- Source dataset: `data/patches_iter6/train`
- Review source: corrected clean-mask `review_consensus.csv`
- Required decision: `include_as_hard_negative=yes` and `binary_label=normal`
- Maximum patches per component: 4
- Maximum new patches per WSI: 64
- Allocation: deterministic rank round-robin across components
- New hard-negative patches: 136

## Dataset counts

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| Source iter6 | 732 | 287 | 1019 |
| Iter7 | 868 | 287 | 1155 |

## Added patches by WSI

| WSI | Patches |
| --- | ---: |
| normal_033 | 4 |
| normal_034 | 64 |
| normal_036 | 4 |
| normal_037 | 64 |

## Added patches by morphology

| Category | Patches |
| --- | ---: |
| fibrosis_stroma_benign | 47 |
| sinus_histiocytosis | 16 |
| vessel_lumen | 73 |
