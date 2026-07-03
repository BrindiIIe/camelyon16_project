# Hard Positive Candidate Review

Model inference CSV directory: `/Volumes/TX/camelyon16_project/data/inference_iter2`
Low probability threshold: `0.5`
Mid probability threshold: `0.8`
Edge margin: `256` pixels
Maximum selected candidates per slide: `24`

Selected candidates: `238`

| Slide | Annotated tumor candidates | Eligible hard positives | Selected | Lowest prob |
| --- | ---: | ---: | ---: | ---: |
| tumor_001 | 688 | 313 | 24 | 0.042 |
| tumor_002 | 35 | 33 | 24 | 0.026 |
| tumor_003 | 421 | 236 | 24 | 0.010 |
| tumor_004 | 323 | 209 | 24 | 0.000 |
| tumor_005 | 143 | 107 | 24 | 0.017 |
| tumor_006 | 105 | 92 | 24 | 0.077 |
| tumor_007 | 147 | 118 | 24 | 0.321 |
| tumor_008 | 22 | 22 | 22 | 0.002 |
| tumor_009 | 50855 | 23858 | 24 | 0.000 |
| tumor_010 | 24 | 24 | 24 | 0.953 |

Review goal: confirm which low/intermediate-probability tumor patches
are true tumor and useful as hard positives for a future iter5 dataset.
Border candidates are included because they may represent small tumor
clusters, partial tumor, crush artefact, fibrosis, necrosis, or transition
zones that are clinically useful for robust training.
