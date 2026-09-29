# Iter2 False-Positive Component Review

Threshold: `0.5`
Minimum component size: `40` patches
Maximum components per slide: `3`
Maximum extracted patches per component: `16`

Extracted components: `15`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_011 | 2 | 49 | 1.000 |
| normal_014 | 1 | 49 | 0.999 |
| normal_016 | 1 | 58 | 0.999 |
| normal_022 | 3 | 212 | 1.000 |
| normal_025 | 3 | 152 | 1.000 |
| normal_028 | 1 | 51 | 0.997 |
| normal_030 | 1 | 142 | 0.999 |
| normal_032 | 3 | 105 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be included as a hard negative for a future model
dataset.
