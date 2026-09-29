# Hard-Mining Protocol v1

This protocol defines how to continue hard mining after the full CAMELYON16 WSI
inventory and slide-level split have been created.

## Goals

- Improve the model by mining informative false positives and difficult true
  positives.
- Avoid leakage from validation or final test data into training.
- Keep every WSI-level inference run traceable and resumable.
- Avoid running full inference on all WSI unnecessarily.

## Data Split Rules

Use:

- `outputs/splits/wsi_split_v1.csv`
- `outputs/splits/wsi_inventory_v1.csv`

Rules:

- `train`: may be used for model training, hard mining, review, and iterative
  enrichment.
- `val`: may be used for threshold selection, WSI rule tuning, and model
  comparison.
- `test_final`: must not be used for hard mining, manual review-driven model
  changes, threshold tuning, or exploratory error correction.

Any slide used for hard-mining review must be marked as such and must remain
outside `test_final`.

## Recommended Iteration Loop

1. Train or select a model checkpoint, e.g. `iter2`.
2. Create an inference queue from the split file.
3. Run WSI inference in small batches with `--resume`.
4. Mine hard negatives from normal training WSI.
5. Mine hard positives from tumor training WSI with annotations.
6. Review extracted candidates manually.
7. Prepare the next training dataset.
8. Retrain.
9. Evaluate on `val` only.
10. Freeze model and WSI decision rules.
11. Evaluate once on `test_final`.

## Inference Strategy

Do not start with all 385 WSI.

Suggested first pass:

- normal train slides only
- exclude slides already used for hard mining if the goal is to discover new
  failure modes
- limit to 20-40 WSI per queue
- use `stride=256` for coarse screening if speed becomes limiting
- re-run selected slides at `stride=128` for detailed extraction

Recommended output naming:

```text
data/inference_<experiment>_<purpose>/
outputs/inference_queues/<queue_name>.csv
```

Examples:

```text
data/inference_iter2_hn_train_screen/
outputs/inference_queues/iter2_hn_train_normals_queue.csv
```

## Hard-Negative Mining

Input:

- model inference CSVs on normal `train` WSI

Candidate rule:

- high-probability tumor predictions on normal slides
- prioritize connected components rather than isolated patches
- start with component-based extraction, e.g. patch threshold 0.6 and minimum
  component size 30

Review:

- categorize benign mimic type
- include only useful hard negatives
- record slide id, component id, category, and include decision
- for the next review batch, use two independent assessments before any
  discussion: one by the junior resident and one by the senior pathologist
  (`PH`)
- keep the two review tables separate and hide the other reviewer's answers
  until both assessments are complete
- compare at least the binary label, morphology category, difficulty type, and
  hard-negative inclusion decision
- report raw agreement as `agreements / jointly reviewed cases`, together with
  Cohen's kappa when the number of cases and category distribution permit it
- discuss disagreements only after the independent answers have been frozen;
  record a consensus answer separately without overwriting either initial
  assessment

Do not mine from `test_final`.

### Inter-Reviewer Comparison

The purpose of the comparison is to measure how reproducible the FP
classification is between observers with different levels of experience, not
to assume in advance that one observer is correct.

For each candidate, preserve three distinct records:

1. the junior resident's initial independent answer;
2. the senior pathologist's initial independent answer;
3. the consensus answer reached after discussion.

Recommended reporting:

- number of cases reviewed by both observers;
- percentage of exact agreement for each review field;
- confusion table for the main categories;
- Cohen's kappa with a cautious interpretation, especially for rare or
  imbalanced categories;
- number and examples of disagreements resolved by consensus.

The manuscript should state that classification was difficult if supported by
the observed agreement and disagreement patterns. It should not state an
expected percentage difference before the measurements are available.

## Hard-Positive Mining

Input:

- model inference CSVs on tumor `train` WSI with XML annotations

Candidate rule:

- annotated tumor patches with low or intermediate tumor probability
- prioritize tumor borders, ITC-like regions, small clusters, necrosis/fibrosis,
  crushed tumor, and artifacts

Review:

- include only true tumor or useful border-transition examples
- exclude annotation noise, non-tumor tissue, and uninformative/easy tumor

Do not mine from `test_final`.

## Validation Use

Use `val` to choose:

- patch probability threshold
- connected-component minimum size
- whether micro-clusters are alert-only or decision-level
- whether a new iteration is worth testing further

If a `val` slide is manually reviewed and used to alter training, move it out
of validation and regenerate the split.

## Final Test Use

Use `test_final` only after:

- model checkpoint is frozen
- WSI inference stride is frozen
- thresholds and decision rules are frozen
- no further hard mining decisions depend on test results

The final test report should state that `test_*` labels were inferred from XML
availability unless official CAMELYON16 test labels are added to the metadata.

## Practical Runtime Control

- Use queues and small `--max-slides` batches.
- Use `--resume` for every inference run.
- Track `status`, `started_at`, `finished_at`, `seconds`, and `notes`.
- Prefer normal WSI first for hard-negative discovery.
- Avoid full all-slide inference until the candidate model looks promising on
  validation.
