# False-Positive Component Review

Threshold: `0.5`
Minimum component size: `40` patches
Maximum components per slide: `3`
Maximum extracted patches per component: `8`

Extracted components: `47`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_049 | 3 | 977 | 1.000 |
| normal_053 | 3 | 245 | 1.000 |
| normal_063 | 2 | 56 | 0.998 |
| normal_100 | 3 | 726 | 1.000 |
| normal_102 | 3 | 263 | 1.000 |
| normal_122 | 3 | 1719 | 1.000 |
| normal_124 | 3 | 308 | 1.000 |
| normal_132 | 3 | 520 | 1.000 |
| normal_136 | 3 | 513 | 1.000 |
| normal_137 | 3 | 778 | 1.000 |
| normal_138 | 3 | 85 | 1.000 |
| normal_140 | 3 | 290 | 1.000 |
| normal_142 | 3 | 84 | 0.997 |
| normal_145 | 3 | 2675 | 1.000 |
| normal_149 | 3 | 223 | 1.000 |
| normal_153 | 3 | 181 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be considered as a hard negative only after the
independent reviews and the separate consensus have been completed.
Extraction alone does not authorize injection into a training dataset.
