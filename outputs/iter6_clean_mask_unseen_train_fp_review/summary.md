# False-Positive Component Review

Threshold: `0.5`
Minimum component size: `40` patches
Maximum components per slide: `20`
Maximum extracted patches per component: `16`

Extracted components: `37`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_033 | 1 | 55 | 0.991 |
| normal_034 | 19 | 425 | 1.000 |
| normal_036 | 1 | 45 | 0.997 |
| normal_037 | 16 | 161 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be considered as a hard negative only after the
independent reviews and the separate consensus have been completed.
Extraction alone does not authorize injection into a training dataset.
