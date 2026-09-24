# Iter8 WSI validation

Completed on all 48 validation WSI (29 normal, 19 tumor), corrected tissue mask, stride 128. Final test untouched.

Frozen rule: probability >= 0.5, component size >= 40.

| Model | sensitivity | specificity | precision | f1 | accuracy | tp | fp | fn | tn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| iter7 | 0.8421052631578947 | 0.4482758620689655 | 0.5 | 0.6274509803921569 | 0.6041666666666666 | 16 | 16 | 3 | 13 |
| iter8 | 0.5789473684210527 | 0.9655172413793104 | 0.9166666666666666 | 0.7096774193548387 | 0.8125 | 11 | 1 | 8 | 28 |

Validation-only grid: outputs/wsi_connected_components_iter8_val_grid/.
Grid settings match iter7; this is validation performance, not final-test performance.
