# Iter8 Dataset Preparation

`iter8` is cumulative: `iter7` plus hard negatives from the reviewed iter8 stratified-screen consensus.

## Selection contract

- Source dataset: `data/patches_iter7/train`
- Review source: stratified-screen `review_consensus.csv`
- Required decision: `include_as_hard_negative=yes` and `binary_label=normal`
- Maximum patches per component: 4
- Maximum new patches per WSI: 64
- Allocation: deterministic rank round-robin across components
- New hard-negative patches: 516

## Dataset counts

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| Source iter7 | 868 | 287 | 1155 |
| Iter8 | 1384 | 287 | 1671 |

## Added patches by WSI

| WSI | Patches |
| --- | ---: |
| normal_036 | 20 |
| normal_038 | 12 |
| normal_045 | 12 |
| normal_048 | 8 |
| normal_052 | 20 |
| normal_055 | 20 |
| normal_067 | 20 |
| normal_070 | 16 |
| normal_077 | 4 |
| normal_080 | 4 |
| normal_087 | 20 |
| normal_089 | 20 |
| normal_096 | 12 |
| normal_103 | 20 |
| normal_106 | 20 |
| normal_108 | 20 |
| normal_111 | 20 |
| normal_114 | 20 |
| normal_117 | 16 |
| normal_119 | 20 |
| normal_123 | 20 |
| normal_126 | 20 |
| normal_129 | 20 |
| normal_133 | 12 |
| normal_135 | 20 |
| normal_143 | 20 |
| normal_146 | 20 |
| normal_150 | 20 |
| normal_152 | 20 |
| normal_156 | 20 |

## Added patches by morphology

| Category | Patches |
| --- | ---: |
| electrocoagulation_artifact | 4 |
| fibrosis_stroma_benign | 228 |
| generic_artifact | 8 |
| macrophage_histiocyte | 104 |
| necrosis_coagulation_benign | 4 |
| sinus_histiocytosis | 40 |
| vessel_lumen | 128 |
