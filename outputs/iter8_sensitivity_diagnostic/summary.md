# Iter8 sensitivity diagnostic

Exploratory validation only: 48 slides, no retraining or final-test access.
No lesion localization is established by slide-level positivity.

## Iter8 false negatives at 0.5/40

| Slide | Iter7 largest component | Iter8 largest component | Iter7 positive |
| --- | ---: | ---: | ---: |
| tumor_017 | 59 | 7 | 1 |
| tumor_040 | 34 | 20 | 0 |
| tumor_043 | 18 | 5 | 0 |
| tumor_067 | 13 | 15 | 0 |
| tumor_071 | 538 | 1 | 1 |
| tumor_074 | 792 | 30 | 1 |
| tumor_081 | 82 | 0 | 1 |
| tumor_096 | 252 | 0 | 1 |

## Best specificity at sensitivity targets

- Sensitivity >= 80%: threshold 0.3, component 10; sensitivity 84.2%, specificity 62.1%, FN 3, FP 11.
- Sensitivity >= 90%: threshold 0.15, component 2; sensitivity 94.7%, specificity 41.4%, FN 1, FP 17.
- Sensitivity >= 95%: threshold 0.25, component 1; sensitivity 100.0%, specificity 27.6%, FN 0, FP 21.
- Sensitivity >= 100%: threshold 0.25, component 1; sensitivity 100.0%, specificity 27.6%, FN 0, FP 21.
