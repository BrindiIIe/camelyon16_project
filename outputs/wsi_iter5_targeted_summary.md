# Iter5 Targeted WSI Inference Summary

Targeted WSI inference was run on six normal slides that generated larger
iter4 false-positive components:

- `normal_001`
- `normal_002`
- `normal_003`
- `normal_008`
- `normal_009`
- `normal_010`

Command:

```bash
myenv_win/Scripts/python.exe -u src/05_infer_wsi.py \
  --model-path models/best_resnet18_patch_iter5.pt \
  --output-dir data/inference_iter5_targeted \
  --device cpu \
  --batch-size 256 \
  --progress-every 10 \
  --resume \
  --slides normal_001.tif normal_002.tif normal_003.tif normal_008.tif normal_009.tif normal_010.tif
```

Observed Windows CPU throughput was about 46-52 patches/second.

Outputs:

- `data/inference_iter5_targeted/*_probs.csv`
- `outputs/wsi_connected_components_iter5_targeted/per_slide_components.csv`
- `outputs/wsi_connected_components_iter5_targeted/summary_components.csv`
- `outputs/wsi_connected_components_iter5_targeted/manuscript_wsi_table.md`

## Key Connected-Component Results

| Rule | Specificity on 6 targeted normal WSI | FP | Notes |
| --- | ---: | ---: | --- |
| patch >= 0.5, component >= 40 | 0.833 | 1 | `normal_009` remains positive |
| patch >= 0.6, component >= 30 | 0.667 | 2 | `normal_008` and `normal_009` positive |
| patch >= 0.8, component >= 20 | 0.667 | 2 | `normal_008` and `normal_009` positive |
| patch >= 0.8, component >= 40 | 1.000 | 0 | Specific on this targeted normal subset |

## Per-Slide Findings At `patch >= 0.5`, Component `>= 40`

| Slide | Max probability | Positive patches | Largest component | Prediction |
| --- | ---: | ---: | ---: | --- |
| `normal_001` | 0.998 | 391 | 23 | negative |
| `normal_002` | 0.996 | 283 | 9 | negative |
| `normal_003` | 0.997 | 380 | 16 | negative |
| `normal_008` | 1.000 | 443 | 37 | negative |
| `normal_009` | 0.999 | 4590 | 153 | positive |
| `normal_010` | 0.999 | 331 | 24 | negative |

## Interpretation

`iter5` reduced several iter4 false-positive connected components, but it
remains too permissive on `normal_009`, where thousands of patches exceed the
0.5 tumor threshold and the largest connected component reaches 153 patches.

This targeted result supports the patch-level finding: `iter5` learned many
reviewed examples but should not replace `iter2` as the reference model without
full WSI-level evidence. If iter5 is explored further, it should be evaluated
with stricter connected-component settings and with tumor WSI included to
verify that sensitivity is not lost.
