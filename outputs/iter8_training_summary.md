# Iter8 Training Summary

Training completed on 2026-09-05: 10 epochs, CPU, batch size 32,
Adam learning rate 1e-4, ImageNet initialization, class weights [1, 2].
Training: 1,384 normal and 287 tumor patches.
Validation: unchanged 189 normal and 29 tumor patches; threshold 0.2.
Best checkpoint selected at epoch 8; epoch 10 tied without replacing it.
Checkpoint: `models/best_resnet18_patch_iter8.pt`.

| Actual class | Predicted normal | Predicted tumor |
| --- | ---: | ---: |
| Normal | 189 | 0 |
| Tumor | 1 | 28 |

Tumor precision: 1.0000; recall: 0.9655; F1: 0.9825.
Accuracy: 217/218 = 0.9954. No errors in the stderr log.
Iter7 had zero false positives and zero false negatives on this validation set;
iter8 has zero false positives and one false negative. WSI-level improvement
is not established and requires clean-mask validation on the 48 val slides.

Run metadata and logs: `outputs/iter8_dataset/training_run.json`.
