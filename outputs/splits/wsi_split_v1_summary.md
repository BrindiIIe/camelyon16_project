# WSI Split v1 Summary

This split is slide-level: every WSI belongs to exactly one split.
Slides used for hard mining are forced into `train` and excluded from the final test set.

## Inventory

| Group | WSI count |
| --- | ---: |
| normal | 155 |
| tumor | 105 |
| test | 125 |

| Label | WSI count |
| --- | ---: |
| normal | 234 |
| tumor | 151 |

For `test_*` slides, labels are inferred from XML availability: XML present = tumor, no XML = assumed normal.

## Split Counts

| Split | Normal | Tumor | Total |
| --- | ---: | ---: | ---: |
| train | 126 | 86 | 212 |
| val | 29 | 19 | 48 |
| test_final | 79 | 46 | 125 |

## Hard-Mining / Prior-Use Slides

Slides marked as used for hard mining: `20`.

| Slide | Label | Split | Hard-mining role | Other roles |
| --- | --- | --- | --- | --- |
| normal_001 | normal | train | iter4_fp_hard_negative_review | iter4_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_002 | normal | train | iter4_fp_hard_negative_review | iter4_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_003 | normal | train | iter4_fp_hard_negative_review | iter4_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_004 | normal | train | micro_fp_hard_negative_review | micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_005 | normal | train | micro_fp_hard_negative_review | micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_006 | normal | train | micro_fp_hard_negative_review | micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_007 | normal | train | micro_fp_hard_negative_review | micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_008 | normal | train | iter4_fp_hard_negative_review;micro_fp_hard_negative_review | iter4_fp_hard_negative_review;micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_009 | normal | train | iter4_fp_hard_negative_review;micro_fp_hard_negative_review | iter4_fp_hard_negative_review;micro_fp_hard_negative_review;prior_20_wsi_exploration |
| normal_010 | normal | train | iter4_fp_hard_negative_review;micro_fp_hard_negative_review | iter4_fp_hard_negative_review;micro_fp_hard_negative_review;prior_20_wsi_exploration |
| tumor_001 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_002 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_003 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_004 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_005 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_006 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_007 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_008 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_009 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |
| tumor_010 | tumor | train | iter2_hard_positive_review | iter2_hard_positive_review;prior_20_wsi_exploration |

## Final Test Set

Final test candidates: `125` WSI.
- Normal: `79`
- Tumor: `46`

No slide currently marked as hard-mining material is assigned to `test_final`.

## Missing / Extra Files

| Expected group | Missing WSI IDs |
| --- | --- |
| normal | normal_086 |
| tumor | tumor_089, tumor_090, tumor_092, tumor_093, tumor_094, tumor_095 |
| test | test_001, test_002, test_049, test_104, test_107 |

XML files without a matching root-level WSI:

test_001, test_002, test_104, tumor_089, tumor_090, tumor_092, tumor_093, tumor_094, tumor_095

## Recommended Use

- Use `train` for patch extraction, model training, and hard-example enrichment.
- Use `val` to tune model thresholds and WSI connected-component rules.
- Use `test_final` only once the pipeline and thresholds are frozen.
