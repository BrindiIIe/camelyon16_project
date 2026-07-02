# Iter4 Patch-Level Training Summary

Command:

```bash
myenv311/bin/python -u src/03_train_model.py --experiment iter4 --device cpu --epochs 10
```

Dataset:

- Train: `data/patches_iter4/train`
- Validation: `data/patches_base/val`
- Train distribution: 618 normal, 287 tumor
- Validation distribution: 189 normal, 29 tumor

Best checkpoint:

- `models/best_resnet18_patch_iter4.pt`
- Best validation F1 was reached at epoch 7 and matched at epoch 8.

Final validation metrics after reloading the best checkpoint:

| Class | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| normal | 1.00 | 0.98 | 0.99 | 189 |
| tumor | 0.88 | 1.00 | 0.94 | 29 |

Confusion matrix:

| | Pred normal | Pred tumor |
| --- | ---: | ---: |
| True normal | 185 | 4 |
| True tumor | 0 | 29 |

Interpretation:

- Patch-level tumor recall is preserved at 1.00.
- Tumor precision is improved compared with early epochs while keeping zero
  tumor false negatives on this validation split.
- The next decision should be based on WSI-level inference and micro-cluster
  false-positive review, not patch-level metrics alone.

