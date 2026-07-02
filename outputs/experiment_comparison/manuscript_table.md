| Expérience | Seuil choisi | Val précision | Val rappel | Val F1 | Val FP | Val FN | Test précision | Test rappel | Test F1 | Test FP | Test FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.2 | 0.686 | 0.828 | 0.750 | 11 | 5 | 0.833 | 1.000 | 0.909 | 2 | 0 |
| iter1 | 0.3 | 0.966 | 0.966 | 0.966 | 1 | 1 | 0.909 | 1.000 | 0.952 | 1 | 0 |
| iter2 | 0.5 | 0.967 | 1.000 | 0.983 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1 | 0 |
| iter3 | 0.5 | 0.966 | 0.966 | 0.966 | 1 | 1 | 1.000 | 0.700 | 0.824 | 0 | 3 |

Seuil choisi sur la validation en maximisant le F1 tumoral; les métriques test utilisent le même seuil.
