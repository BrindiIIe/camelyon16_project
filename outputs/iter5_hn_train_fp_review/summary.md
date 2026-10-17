# Iter5 False-Positive Component Review

Threshold: `0.5`
Minimum component size: `40` patches
Maximum components per slide: `3`
Maximum extracted patches per component: `16`

Extracted components: `15`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_011 | 3 | 211 | 1.000 |
| normal_022 | 3 | 104 | 1.000 |
| normal_025 | 3 | 66 | 1.000 |
| normal_028 | 3 | 186 | 0.999 |
| normal_032 | 3 | 2632 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be included as a hard negative for a future model
dataset.
