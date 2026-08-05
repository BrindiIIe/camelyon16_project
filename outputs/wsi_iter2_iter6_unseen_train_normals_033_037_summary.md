# Iter2 versus iter6 on unseen normal train WSI

Date: 2026-07-18

## Cohort and purpose

The comparison uses five consecutive normal slides from the `train` split:
`normal_033` to `normal_037`. None had been reviewed, explored, or used for
hard mining before this experiment. Both models were run with the same WSI
inference settings (patch size 256, stride 128, CPU, batch size 256).

This is an internal generalization pilot on unseen training slides. It is more
informative than re-testing only the hard-mining source slides, but it is not a
final validation result and must not be presented as such.

## Aggregate comparison

| WSI rule | Model | FP slides | Specificity | Positive patches | Largest component |
| --- | --- | ---: | ---: | ---: | ---: |
| patch >= 0.5, component >= 40 | iter2 | 4/5 | 0.200 | 26,749 | 1,043 |
| patch >= 0.5, component >= 40 | iter6 | 3/5 | 0.400 | 8,655 | 100 |
| patch >= 0.6, component >= 30 | iter2 | 5/5 | 0.000 | 21,820 | 633 |
| patch >= 0.6, component >= 30 | iter6 | 3/5 | 0.400 | 6,907 | 85 |
| patch >= 0.8, component >= 20 | iter2 | 4/5 | 0.200 | 12,648 | 292 |
| patch >= 0.8, component >= 20 | iter6 | 3/5 | 0.400 | 3,817 | 55 |

At the main `0.5 / 40` rule, iter6 reduces the FP-slide count from 4 to 3,
the total number of positive patches by 67.6%, and the largest connected
component by 90.4% relative to iter2.

## Main-rule result by slide

| Slide | iter2 positive patches | iter2 largest component | iter2 FP | iter6 positive patches | iter6 largest component | iter6 FP |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| normal_033 | 877 | 35 | no | 379 | 12 | no |
| normal_034 | 11,399 | 453 | yes | 3,246 | 82 | yes |
| normal_035 | 642 | 53 | yes | 1,684 | 99 | yes |
| normal_036 | 5,525 | 1,043 | yes | 712 | 19 | no |
| normal_037 | 8,306 | 443 | yes | 2,634 | 100 | yes |

Iter6 corrects `normal_036` at the main rule and markedly reduces FP burden on
most slides. `normal_035` is the exception: its positive-patch count and
largest component increase under iter6, so its morphology deserves particular
attention during review.

## Decision

The remaining iter6 FP components from `normal_034`, `normal_035`, and
`normal_037` should be extracted for blinded independent review by the junior
resident and the senior pathologist. They must not be injected into another
training iteration before both initial reviews are frozen, agreement is
measured, and a separate consensus file is produced.

Thresholds should subsequently be tuned on the `val` split. The final test
split remains untouched until the model and WSI decision rule are frozen.
