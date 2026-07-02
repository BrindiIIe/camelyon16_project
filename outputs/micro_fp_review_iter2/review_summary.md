# Micro-Cluster False-Positive Review - Iter2

Review performed on normal WSI micro-clusters extracted with:

```text
micro_threshold = 0.99
min_component_size = 2 connected patches
model = iter2
```

## Summary

The micro-cluster rule detected 11 high-confidence clusters on normal WSI.
All reviewed clusters were interpreted as benign or artefactual. This confirms
that the micro-cluster mode is sensitive but not specific enough to be used as
an automatic WSI-level positive rule.

Recommended interpretation:

- Keep the large connected-component rule as the main automatic WSI decision.
- Use micro-clusters as a review/alert mode for tiny suspicious regions.
- Use only selected reviewed benign mimics as hard negatives for a future
  `iter4`, rather than adding all clusters indiscriminately.

## Review Decisions

| Slide | Component | Interpretation | Include as hard negative |
| --- | ---: | --- | --- |
| normal_004 | 1 | Possible vessel/lumen or detached fragment; benign, no real doubt | no |
| normal_005 | 1 | Large macrophage with crushed lymphocytes; benign, no real doubt | no |
| normal_006 | 1 | Single suspicious cell in clarified cytoplasm or artefactual cavity | yes |
| normal_007 | 1 | Fibrous/extraganglionic area, likely distant adipose trabecula | no |
| normal_008 | 1 | Lymphocytes and macrophages without concerning feature | no |
| normal_009 | 1 | Benign fibrous tissue with macrophages, somewhat unusual representation | maybe |
| normal_009 | 2 | Mildly suspicious cellular cluster, probably macrophagic | yes |
| normal_010 | 1 | Fibrous/coagulative-necrosis-like benign area | maybe |
| normal_010 | 2 | Fibrous/coagulative-necrosis-like benign area | maybe |
| normal_010 | 3 | Fibrous/coagulative-necrosis-like benign area | maybe |
| normal_010 | 4 | Fibrous/coagulative-necrosis-like benign area | maybe |

## Hard-Negative Recommendation

Priority hard negatives for `iter4`:

- `normal_006`, component 1
- `normal_009`, component 2

Optional hard negatives:

- `normal_009`, component 1
- `normal_010`, components 1-4

Do not prioritize:

- `normal_004`, component 1
- `normal_005`, component 1
- `normal_007`, component 1
- `normal_008`, component 1

