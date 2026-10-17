# Iter2 vs Iter5 vs Iter6 on Hard-Negative Source WSI

This targeted correction check compares the three models on the five normal
training WSI that supplied the 15 reviewed FP components used to build
`iter6`: `normal_011`, `normal_022`, `normal_025`, `normal_028`, and
`normal_032`.

All inference runs used 256 x 256 patches, stride 128, and the same connected-
component definitions. Because these slides contributed training examples,
this is a correction/memorization check and not independent evidence of
generalization.

## Rule-Level Comparison

| Rule | Model | FP slides | Specificity | Largest component observed | Positive patches |
| --- | --- | ---: | ---: | ---: | ---: |
| patch >= 0.5, component >= 40 | iter2 | 5/5 | 0.000 | 212 | 11187 |
| patch >= 0.5, component >= 40 | iter5 | 5/5 | 0.000 | 2632 | 24966 |
| patch >= 0.5, component >= 40 | iter6 | 2/5 | 0.600 | 111 | 6132 |
| patch >= 0.6, component >= 30 | iter2 | 4/5 | 0.200 | 149 | 8725 |
| patch >= 0.6, component >= 30 | iter5 | 5/5 | 0.000 | 2272 | 20436 |
| patch >= 0.6, component >= 30 | iter6 | 3/5 | 0.400 | 105 | 4864 |
| patch >= 0.8, component >= 20 | iter2 | 4/5 | 0.200 | 91 | 4718 |
| patch >= 0.8, component >= 20 | iter5 | 5/5 | 0.000 | 615 | 12325 |
| patch >= 0.8, component >= 20 | iter6 | 3/5 | 0.400 | 64 | 2674 |

## Main Rule Detail (0.5 / 40)

| Slide | Iter2 largest | Iter2 prediction | Iter5 largest | Iter5 prediction | Iter6 largest | Iter6 prediction |
| --- | ---: | --- | ---: | --- | ---: | --- |
| normal_011 | 49 | FP | 211 | FP | 36 | normal |
| normal_022 | 212 | FP | 104 | FP | 79 | FP |
| normal_025 | 152 | FP | 66 | FP | 17 | normal |
| normal_028 | 51 | FP | 186 | FP | 111 | FP |
| normal_032 | 105 | FP | 2632 | FP | 26 | normal |

## Interpretation

At the main `0.5 / 40` rule, `iter6` corrects three of the five source WSI and
reduces the number of FP slides from 5 to 2. It also markedly reduces the
overall number of positive patches compared with both `iter2` and `iter5`.

The remaining source-slide problems are `normal_022` and `normal_028`. They
should not be injected again immediately: the next priority is testing
`iter6` on new normal training WSI that were not used for review or training.
Only that new-slide check can show whether the reduction generalizes.
