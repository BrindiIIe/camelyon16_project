# False-Positive Component Review

Threshold: `0.5`
Minimum component size: `20` patches
Maximum components per slide: `5`
Maximum extracted patches per component: `8`

Extracted components: `133`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_036 | 5 | 50 | 1.000 |
| normal_038 | 3 | 41 | 0.998 |
| normal_045 | 3 | 67 | 1.000 |
| normal_048 | 2 | 43 | 0.999 |
| normal_052 | 5 | 63 | 1.000 |
| normal_055 | 5 | 254 | 1.000 |
| normal_058 | 1 | 36 | 0.999 |
| normal_067 | 5 | 154 | 1.000 |
| normal_070 | 4 | 98 | 1.000 |
| normal_077 | 1 | 34 | 1.000 |
| normal_080 | 1 | 20 | 0.997 |
| normal_087 | 5 | 48 | 1.000 |
| normal_089 | 5 | 63 | 1.000 |
| normal_096 | 3 | 35 | 0.999 |
| normal_103 | 5 | 1389 | 1.000 |
| normal_106 | 5 | 317 | 1.000 |
| normal_108 | 5 | 301 | 1.000 |
| normal_111 | 5 | 346 | 1.000 |
| normal_114 | 5 | 8246 | 1.000 |
| normal_117 | 5 | 71 | 1.000 |
| normal_119 | 5 | 468 | 1.000 |
| normal_123 | 5 | 127 | 1.000 |
| normal_126 | 5 | 98 | 1.000 |
| normal_129 | 5 | 534 | 1.000 |
| normal_133 | 5 | 186 | 1.000 |
| normal_135 | 5 | 110 | 1.000 |
| normal_143 | 5 | 733 | 1.000 |
| normal_146 | 5 | 377 | 1.000 |
| normal_150 | 5 | 240 | 1.000 |
| normal_152 | 5 | 323 | 1.000 |
| normal_156 | 5 | 118 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be considered as a hard negative only after the
independent reviews and the separate consensus have been completed.
Extraction alone does not authorize injection into a training dataset.
