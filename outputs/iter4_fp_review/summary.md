# Iter4 False-Positive Component Review

Threshold: `0.6`
Minimum component size: `30` patches
Maximum components per slide: `5`
Maximum extracted patches per component: `16`

Extracted components: `12`

| Slide | Components | Largest component | Max probability |
| --- | ---: | ---: | ---: |
| normal_001 | 1 | 89 | 1.000 |
| normal_002 | 2 | 75 | 1.000 |
| normal_003 | 5 | 201 | 1.000 |
| normal_008 | 2 | 45 | 1.000 |
| normal_009 | 1 | 32 | 0.998 |
| normal_010 | 1 | 90 | 0.999 |

Review goal: decide whether each component is benign/artefactual and
whether it should be included as a hard negative for a future iter5
dataset.
