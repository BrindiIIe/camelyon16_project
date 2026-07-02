# Micro False-Positive Patch Probabilities: Iter2 vs Iter4

This compares the already extracted iter2 micro false-positive review patches.
It does not replace full WSI inference, but it tests whether iter4 learned to downscore the reviewed hard negatives.

| Slide | Component | Decision | Category | N | Mean iter2 | Mean iter4 | Delta | Iter2 >= 0.99 | Iter4 >= 0.99 |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normal_004 | 1 | no | benign_lumen_or_detached_fragment | 2 | 0.997 | 0.736 | -0.262 | 2 | 0 |
| normal_005 | 1 | no | benign_macrophage_crush | 2 | 0.998 | 0.783 | -0.215 | 2 | 0 |
| normal_006 | 1 | yes | suspicious_single_cell_artifact | 4 | 1.000 | 0.034 | -0.966 | 4 | 0 |
| normal_007 | 1 | no | benign_fibrous_extraganglionic | 7 | 0.998 | 0.999 | 0.001 | 7 | 7 |
| normal_008 | 1 | no | benign_lymphocytes_macrophages | 6 | 0.998 | 0.923 | -0.075 | 6 | 4 |
| normal_009 | 1 | maybe | benign_unusual_fibrous_macrophages | 3 | 0.994 | 0.941 | -0.053 | 3 | 0 |
| normal_009 | 2 | yes | suspicious_probably_macrophagic | 2 | 0.995 | 0.013 | -0.982 | 2 | 0 |
| normal_010 | 1 | maybe | benign_fibrous_or_coagulative_necrosis | 4 | 0.994 | 0.957 | -0.037 | 4 | 0 |
| normal_010 | 2 | maybe | benign_fibrous_or_coagulative_necrosis | 3 | 0.992 | 0.619 | -0.373 | 3 | 0 |
| normal_010 | 3 | maybe | benign_fibrous_or_coagulative_necrosis | 2 | 1.000 | 0.990 | -0.009 | 2 | 1 |
| normal_010 | 4 | maybe | benign_fibrous_or_coagulative_necrosis | 2 | 0.991 | 0.988 | -0.002 | 2 | 0 |
