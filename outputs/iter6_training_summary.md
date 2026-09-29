# Iter6 Training Summary

`iter6` was trained from the reference `iter2` dataset plus 120 newly reviewed
hard-negative patches (eight patches from each of 15 FP components).

## Training

```bash
myenv_win/Scripts/python.exe -u src/03_train_model.py --experiment iter6 --device cpu --epochs 10
```

- Training distribution: 732 normal, 287 tumor patches.
- Validation distribution: 189 normal, 29 tumor patches.
- Best checkpoint: epoch 10.
- Checkpoint: `models/best_resnet18_patch_iter6.pt`.

## Final Validation Result

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 188 | 1 |
| True tumor | 0 | 29 |

| Class | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| normal | 1.000 | 0.995 | 0.997 | 189 |
| tumor | 0.967 | 1.000 | 0.983 | 29 |

## Interpretation

On the unchanged patch validation set, `iter6` matches the previously reported
`iter2` tumor metrics (precision 0.967, recall 1.000, F1 0.983). This suggests
that adding the 120 new hard negatives did not degrade patch-level validation
sensitivity or precision. WSI-level checks are still required before deciding
whether `iter6` improves false-positive behavior on new slides.
