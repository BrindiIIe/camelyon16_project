# Iter7 Training Summary

`iter7` was trained from the cumulative `iter6` dataset plus 136 corrected
clean-mask consensus hard-negative patches.

## Training

```bash
myenv_win/Scripts/python.exe -u src/03_train_model.py --experiment iter7 --device cpu --epochs 10
```

- Training distribution: 868 normal, 287 tumor patches.
- Validation distribution: 189 normal, 29 tumor patches.
- Validation tumor-probability threshold: 0.2.
- Best checkpoint: epoch 9.
- Checkpoint: `models/best_resnet18_patch_iter7.pt`.

## Final Validation Result

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 189 | 0 |
| True tumor | 0 | 29 |

| Class | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| normal | 1.000 | 1.000 | 1.000 | 189 |
| tumor | 1.000 | 1.000 | 1.000 | 29 |

## Interpretation

On the unchanged patch validation set, `iter7` improves over the recorded
`iter6` result by removing its single normal false positive while preserving
all 29 tumor detections. This is a patch-level result only. WSI-level
validation with the frozen clean tissue-mask pipeline is required before the
model or its decision rule can be frozen.
