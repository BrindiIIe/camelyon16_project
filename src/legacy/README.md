# Legacy scripts

These scripts are kept for reference but are no longer aligned with the active
project layout.

- `review_normal_patches.py` and `review_tumor_patches.py` expect
  `data/patches_split/train/*_keep` review folders that are not part of the
  current active workflow.
- `06_make_train_csv.py` builds a CSV from the old `*_keep` folders.
- `infer_for_hard_negatives.py` uses an obsolete model path
  (`../best_resnet18_patch.pt`) and is superseded by `05_infer_wsi.py` plus
  `extract_hard_negatives.py`.

Current active training data is organized around `data/patches_iter3/train`,
with validation/evaluation kept on `data/patches_base/val` and
`data/patches_base/test`.
