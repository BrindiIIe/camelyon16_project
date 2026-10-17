# False-Positive Component Review

Threshold: `0.5`
Minimum component size: `40` patches
Maximum components per slide: `100`
Maximum extracted patches per component: `16`

Extracted components: `16`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_034 | 4 | 82 | 1.000 |
| normal_035 | 10 | 99 | 1.000 |
| normal_037 | 2 | 100 | 1.000 |

Review goal: decide whether each component is benign/artefactual and
whether it should be considered as a hard negative only after the
independent reviews and the separate consensus have been completed.
Extraction alone does not authorize injection into a training dataset.
