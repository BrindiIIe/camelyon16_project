# WSI Iter2 vs Iter4 Summary

Date: 2026-07-03

Full iter4 WSI inference completed on the current 20-slide cohort:

- 10 tumor WSI: `tumor_001` to `tumor_010`
- 10 normal WSI: `normal_001` to `normal_010`
- Iter4 outputs: `data/inference_iter4/*_probs.csv`

## Main Result

Iter4 is not better than iter2 at WSI level on the current 20 WSI. Iter4 keeps
high sensitivity, but it produces substantially more false-positive normal WSI
under connected-component decision rules.

## Best Connected-Component Results

| Model | Rule | Sensitivity | Specificity | Precision | F1 | TP | FP | FN | TN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| iter2 | patch >= 0.80, component >= 20 | 1.000 | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 | 10 |
| iter2 | patch >= 0.60, component >= 30 | 1.000 | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 | 10 |
| iter2 | patch >= 0.50, component >= 40 | 1.000 | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 | 10 |
| iter4 | best observed: patch >= 0.70, component >= 75 | 1.000 | 0.800 | 0.833 | 0.909 | 10 | 2 | 0 | 8 |
| iter4 | patch >= 0.80, component >= 75 | 0.900 | 0.900 | 0.900 | 0.900 | 9 | 1 | 1 | 9 |
| iter4 | patch >= 0.60, component >= 100 | 0.900 | 0.900 | 0.900 | 0.900 | 9 | 1 | 1 | 9 |

## Comparable Rules

| Rule | Model | Sensitivity | Specificity | Precision | F1 | FP normal WSI |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| patch >= 0.60, component >= 30 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | none |
| patch >= 0.60, component >= 30 | iter4 | 1.000 | 0.400 | 0.625 | 0.769 | normal_001, normal_002, normal_003, normal_008, normal_009, normal_010 |
| patch >= 0.50, component >= 40 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | none |
| patch >= 0.50, component >= 40 | iter4 | 1.000 | 0.400 | 0.625 | 0.769 | normal_001, normal_002, normal_003, normal_007, normal_008, normal_010 |
| patch >= 0.80, component >= 20 | iter2 | 1.000 | 1.000 | 1.000 | 1.000 | none |
| patch >= 0.80, component >= 20 | iter4 | 1.000 | 0.200 | 0.556 | 0.714 | normal_001, normal_002, normal_003, normal_006, normal_007, normal_008, normal_009, normal_010 |

## Interpretation

The targeted iter4 hard-negative training worked on the specific reviewed
micro false-positive patches, but it did not generalize into better WSI-level
specificity. For the thesis pipeline, iter2 should remain the reference model.

Iter4 should be treated as an exploratory experiment showing that small,
selective hard-negative additions can overfit local mimics. The next useful
step is not to promote iter4, but to review iter4 false-positive components and
either:

- build a broader, more representative hard-negative set, or
- freeze iter2 as the main model and proceed with WSI-level validation,
  thresholding, visual review, and manuscript-ready tables.

