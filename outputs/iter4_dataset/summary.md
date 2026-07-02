# Iter4 Dataset Preparation

`iter4` is built from `data/patches_iter2/train` plus reviewed micro false-positive hard negatives.

## Selection

- Included `yes` decisions: always
- Included `maybe` decisions: no
- Added hard-negative patches: 6

## Counts

| Dataset | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| Source iter2 | 612 | 287 | 899 |
| Iter4 | 618 | 287 | 905 |

## Added Components

| Slide | Component | Decision | Category | Added patches |
| --- | ---: | --- | --- | ---: |
| normal_006 | 1 | yes | suspicious_single_cell_artifact | 4 |
| normal_009 | 2 | yes | suspicious_probably_macrophagic | 2 |
